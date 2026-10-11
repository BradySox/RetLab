----- Ballistic Missile Strike -----
-- Lets players direct surface-to-surface ballistic/theatre missile strikes from
-- friendly launchers (Scud-B, 9K720 Iskander, ATACMS, ...) onto positions marked
-- on the F10 map: pick a marker, pick a number of rounds.
-- Ported from CleeeCATCH/dcs-retribution. docs/dev/retlab-features.md, the
-- section "Ballistic missile call-for-fire".
--
-- Multi-round launchers are first class: a 9K720 TEL carries two 9M723 rounds and
-- rounds are counted, fired and reported individually. The launchers are real
-- tracked units firing real weapons; nothing is spawned.
----------------------------------------------------------------

-- Script control functions:
--AddBMBattery(GroupName, Callsign, MaxRangeMeters)		--register a launcher group; ignored if it carries no missiles
--AddBMObserver(UnitName)								--register a unit that may call strikes

----------------------------------------------------------------

env.info("DCSRetribution|Ballistic Missile Strike plugin - Imported")

BMS = {}
BMS.Batteries = {}											--[groupName] = {callsign = ..., maxRange = ..., minRange = ...}
BMS.Observers = {}											--[unitName] = {id = groupID, active = true, rootPath = ...}
BMS.Marks = {[1] = {}, [2] = {}}							--map markers, per coalition
BMS.Missions = {}											--[groupName] = fire mission in progress
BMS.Cooldowns = {}											--[groupName] = mission time the battery is ready again
BMS.PreHeated = {}											--[coalitionId] = true once its launchers have been woken up

-- Tunables. The configuration script overrides these from the plugin options.
BMS.CooldownSeconds = 600									--matches the 9K720's 600s reload time
BMS.LaunchTimeoutSeconds = 900								--first round can take a long time: see the note on spin-up below
BMS.RoundGapSeconds = 180									--no round in this long mid-salvo means the launcher stalled
BMS.MaxRetasks = 1											--re-issue the fire order at most this many times per mission
BMS.ImpactRadiusMeters = 50									--aimpoint scatter handed to FireAtPoint
BMS.MaxRoundsPerMission = 2									--a 9K720 TEL carries two rounds
BMS.MaxRangeOverrideMeters = 0								--0 means "use each launcher's own range"
BMS.PreHeatLaunchers = true
BMS.ReserveForPlayers = true
BMS.MaxMarksListed = 8										--keep the radio menu navigable
BMS.WeaponFlag = 3221225470									--Weapon.flag.Auto: a TEL carries nothing else
BMS.RoundSpeedMps = 1000									--only used for the "impact in" estimate
BMS.MenuName = "Ballistic Missile Strike"

-- Ballistic missiles have a minimum range as well as a maximum one, and DCS
-- exposes neither to the scripting engine. A launcher handed a target inside
-- its minimum range accepts the task and then silently never fires, so the
-- numbers from the unit definitions are kept here to turn that into an answer
-- the player can act on. Anything not listed falls back to no minimum and is
-- caught by the launch watchdog instead.
BMS.MinRangeByType = {
	["CHAP_9K720_HE"] = 75000,								--9M723 HE, distanceMin 75 km
	["CHAP_9K720_Cluster"] = 75000,							--9M723 cluster
	["CH_IskanderM"] = 75000,								--pre-2.9 Currenthill mod id for the same TEL
	["Scud_B"] = 50000,										--R-17
	["CH_M270A1_ATACMS"] = 50000,							--ATACMS M39A1/M48, distanceMin 50 km
	["CHAP_M142_ATACMS_M48"] = 50000,
	["IRAD_Sejjil_TEL"] = 75000,							--the Iranian pack's four fly ED's 9M723: 75-400 km
	["IRAD_Emad_TEL"] = 75000,
	["IRAD_Kheibar_TEL"] = 75000,
	["IRAD_Fattah2_TEL"] = 75000,
}

local function NM(meters)
	return math.floor(meters / 1852)
end

----- Ammunition -----

-- Registration already restricts us to launcher groups, so anything of missile
-- category is a round. Descriptors from mods occasionally omit the category;
-- count those too rather than reporting an armed launcher as empty.
local function IsRound(desc)
	if not desc or desc.category == nil then
		return true
	end
	return desc.category == Weapon.Category.MISSILE
end

local function CountRounds(GroupName)
	local group = Group.getByName(GroupName)
	if not group then
		return 0
	end
	local total = 0
	for _, unit in pairs(group:getUnits() or {}) do
		local ammo = unit:getAmmo()
		if ammo then
			for a = 1, #ammo do
				if IsRound(ammo[a].desc) then
					total = total + ammo[a].count
				end
			end
		end
	end
	return total
end

local function RoundName(GroupName)
	local group = Group.getByName(GroupName)
	if not group then
		return "missile"
	end
	for _, unit in pairs(group:getUnits() or {}) do
		local ammo = unit:getAmmo()
		if ammo then
			for a = 1, #ammo do
				local desc = ammo[a].desc
				if IsRound(desc) and desc and desc.displayName and desc.displayName ~= "" then
					return desc.displayName
				end
			end
		end
	end
	return "missile"
end

local function MinRangeFor(GroupName)
	local group = Group.getByName(GroupName)
	if not group then
		return 0
	end
	local minRange = 0
	for _, unit in pairs(group:getUnits() or {}) do
		local listed = BMS.MinRangeByType[unit:getTypeName()]
		if listed and listed > minRange then
			minRange = listed
		end
	end
	return minRange
end

----- Registration -----

function AddBMBattery(GroupName, Callsign, MaxRangeMeters)
	local group = Group.getByName(GroupName)
	if not group then
		return false
	end
	if CountRounds(GroupName) == 0 then						--e.g. a V-1 ramp, which carries nothing DCS can fire
		return false
	end
	BMS.Batteries[GroupName] = {
		callsign = Callsign or GroupName,
		maxRange = MaxRangeMeters or 0,
		minRange = MinRangeFor(GroupName),
	}
	return true
end

function AddBMObserver(UnitName)
	if BMS.Observers[UnitName] == nil then
		BMS.Observers[UnitName] = {}
	end
end

local function MaxRangeFor(GroupName)
	if BMS.MaxRangeOverrideMeters > 0 then
		return BMS.MaxRangeOverrideMeters
	end
	local battery = BMS.Batteries[GroupName]
	if battery and battery.maxRange > 0 then
		return battery.maxRange
	end
	return 400000
end

----- Map markers -----

local function OnMarkAdded(event)
	if event.coalition == 1 or event.coalition == 2 then
		table.insert(BMS.Marks[event.coalition], event)
	else													--not coalition specific, visible to both
		table.insert(BMS.Marks[1], event)
		table.insert(BMS.Marks[2], event)
	end
end

local function OnMarkRemoved(event)
	for c = 1, 2 do
		for i = #BMS.Marks[c], 1, -1 do
			if BMS.Marks[c][i].idx == event.idx then
				table.remove(BMS.Marks[c], i)
			end
		end
	end
end

local function MarkLabel(mark)
	if mark.text and mark.text ~= "" then
		return string.sub(mark.text, 1, 20)
	end
	local lat, lon = coord.LOtoLL(mark.pos)
	local mgrs = coord.LLtoMGRS(lat, lon)
	return mgrs.MGRSDigraph .. " " .. math.floor(mgrs.Easting / 100) .. " " .. math.floor(mgrs.Northing / 100)
end

local function FindMark(coalitionId, markIdx)
	for _, mark in pairs(BMS.Marks[coalitionId] or {}) do
		if mark.idx == markIdx then
			return mark
		end
	end
	return nil
end

----- Fire mission -----

local function Distance(a, b)
	local dx = a.x - b.x
	local dz = a.z - b.z
	return math.sqrt(dx * dx + dz * dz)
end

local function Say(mission, text)
	trigger.action.outTextForCoalition(mission.coalition, mission.callsign .. ": " .. text, 20)
end

-- The AI fires the whole remaining salvo from one task. Rounds that never leave
-- the rail are picked up by the supervisor below, which re-issues the order.
local function TaskBattery(mission)
	local group = Group.getByName(mission.battery)
	if not group then
		return false
	end
	local remaining = mission.requested - mission.delivered
	if remaining < 1 then
		return false
	end
	group:getController():setTask({
		id = "ControlledTask",
		params = {
			task = {
				id = "FireAtPoint",
				params = {
					-- The MBot artillery script fires with x/y/zoneRadius, the
					-- scripting docs describe point/radius. Send both spellings;
					-- DCS ignores the params a task does not use.
					x = mission.point.x,
					y = mission.point.z,
					point = {x = mission.point.x, y = mission.point.z},
					zoneRadius = BMS.ImpactRadiusMeters,
					radius = BMS.ImpactRadiusMeters,
					expendQty = remaining,
					expendQtyEnabled = true,
					weaponType = BMS.WeaponFlag,
					templateId = "",
				},
			},
			stopCondition = {
				duration = BMS.LaunchTimeoutSeconds + 300,
			},
		},
	})
	mission.tasked = timer.getTime()
	mission.taskBaseline = CountRounds(mission.battery)
	return true
end

local function EndMission(mission, text)
	BMS.Missions[mission.battery] = nil
	BMS.Cooldowns[mission.battery] = timer.getTime() + BMS.CooldownSeconds
	if text then
		Say(mission, text)
	end
	local group = Group.getByName(mission.battery)
	if group then
		group:getController():resetTask()
	end
	BMS.BuildMenu(mission.observer)
end

-- Poll the round rather than guessing its time of flight: it lets a
-- shoot-down be reported as one, and works for any missile.
local function TrackRound(arg)
	local weapon, mission, label = arg[1], arg[2], arg[3]
	if weapon:isExist() then
		return timer.getTime() + 5
	end
	trigger.action.outTextForCoalition(mission.coalition,
		mission.callsign .. ": splash, " .. label .. ", out.", 20)
	return nil
end

local function OnShot(event)
	if not event.initiator then
		return
	end
	local ok, groupName = pcall(function() return event.initiator:getGroup():getName() end)
	if not ok or not groupName then
		return
	end
	local mission = BMS.Missions[groupName]
	if not mission then
		return
	end
	mission.shots = mission.shots + 1
	mission.lastShot = timer.getTime()
	local eta = math.max(1, math.floor(mission.range / BMS.RoundSpeedMps / 60 + 0.5))
	Say(mission, "shot, round " .. mission.shots .. " of " .. mission.requested
		.. " on " .. mission.label .. ", impact in approximately " .. eta .. " minute(s), out.")
	if event.weapon then
		timer.scheduleFunction(TrackRound, {event.weapon, mission, mission.label}, timer.getTime() + 5)
	end
end

BMSEventHandler = {}
function BMSEventHandler:onEvent(event)
	if event.id == world.event.S_EVENT_MARK_ADDED then
		OnMarkAdded(event)
	elseif event.id == world.event.S_EVENT_MARK_REMOVED then
		OnMarkRemoved(event)
	elseif event.id == world.event.S_EVENT_SHOT then
		-- A handler that throws is dropped by DCS for the rest of the mission,
		-- and shot events arrive for objects that may already be gone.
		local ok, err = pcall(OnShot, event)
		if not ok then
			env.warning("DCSRetribution|Ballistic Missile Strike plugin - shot handler: " .. tostring(err))
		end
	end
end
world.addEventHandler(BMSEventHandler)

local function Fire(arg)
	local unitName, groupName, markIdx, rounds = arg[1], arg[2], arg[3], arg[4]

	local unit = Unit.getByName(unitName)
	if not unit then
		return
	end
	local coalitionId = unit:getCoalition()

	local group = Group.getByName(groupName)
	local battery = BMS.Batteries[groupName]
	if not group or not battery then
		trigger.action.outTextForCoalition(coalitionId, "Strike request failed: that battery is no longer in action.", 15)
		BMS.BuildMenu(unitName)
		return
	end
	local callsign = battery.callsign

	if BMS.Missions[groupName] then
		trigger.action.outTextForCoalition(coalitionId, callsign .. ": negative, fire mission already in progress, out.", 15)
		return
	end

	local readyAt = BMS.Cooldowns[groupName]
	if readyAt and timer.getTime() < readyAt then
		local wait = math.floor((readyAt - timer.getTime()) / 60) + 1
		trigger.action.outTextForCoalition(coalitionId, callsign .. ": negative, reloading, ready in " .. wait .. " minute(s), out.", 15)
		return
	end

	-- The marker may have been dragged or deleted since the menu was built.
	local mark = FindMark(coalitionId, markIdx)
	if not mark then
		trigger.action.outTextForCoalition(coalitionId, callsign .. ": that target marker no longer exists, out.", 15)
		BMS.BuildMenu(unitName)
		return
	end

	local available = CountRounds(groupName)
	if available == 0 then
		trigger.action.outTextForCoalition(coalitionId, callsign .. ": negative, no rounds remaining, out.", 15)
		BMS.BuildMenu(unitName)
		return
	end
	if rounds > available then
		rounds = available
	end

	-- getUnit(1) is nil once the first launcher in the group is destroyed, so
	-- measure from whichever one is still alive.
	local launcher = (group:getUnits() or {})[1]
	if not launcher then
		trigger.action.outTextForCoalition(coalitionId, callsign .. ": battery is out of action, out.", 15)
		BMS.BuildMenu(unitName)
		return
	end

	local range = Distance(launcher:getPoint(), mark.pos)
	local maxRange = MaxRangeFor(groupName)
	if range > maxRange then
		trigger.action.outTextForCoalition(coalitionId, callsign .. ": negative, target out of range at "
			.. NM(range) .. " NM, maximum " .. NM(maxRange) .. " NM, out.", 15)
		return
	end
	if battery.minRange > 0 and range < battery.minRange then
		trigger.action.outTextForCoalition(coalitionId, callsign .. ": negative, target inside minimum range at "
			.. NM(range) .. " NM, minimum " .. NM(battery.minRange) .. " NM, out.", 15)
		return
	end

	local mission = {
		battery = groupName,
		callsign = callsign,
		coalition = coalitionId,
		observer = unitName,
		point = {x = mark.pos.x, z = mark.pos.z},
		label = MarkLabel(mark),
		range = range,
		requested = rounds,				--rounds ordered; never mutated, so reports stay honest
		delivered = 0,					--rounds that have actually left the launcher
		shots = 0,						--shot events seen, for the immediate "round N of M" call
		retasks = 0,
		ammoAtStart = available,
		started = timer.getTime(),
	}
	BMS.Missions[groupName] = mission

	if not TaskBattery(mission) then
		BMS.Missions[groupName] = nil
		trigger.action.outTextForCoalition(coalitionId, callsign .. ": unable to accept the mission, out.", 15)
		return
	end

	-- A 9K720 needs its support legs and launcher up (~45s) and its rounds
	-- aligned (a 600s switch-on delay in the unit definition) before the first
	-- one leaves the rail. Say so, or the player assumes the order was lost.
	Say(mission, "fire mission acknowledged, " .. rounds .. " round(s) of " .. RoundName(groupName)
		.. " on " .. mission.label .. ", " .. NM(range)
		.. " NM, launcher erecting, stand by, out.")
	BMS.BuildMenu(unitName)
end

local function CheckFire(arg)
	local unitName, groupName = arg[1], arg[2]
	local mission = BMS.Missions[groupName]
	if not mission then
		local unit = Unit.getByName(unitName)
		if unit then
			trigger.action.outTextForCoalition(unit:getCoalition(), "No fire mission in progress for that battery.", 10)
		end
		return
	end
	EndMission(mission, "check fire, end of mission, out.")
end

----- Fire mission supervisor -----

-- Ammo count is the authority on what actually launched: shot events can be
-- missed, and a launcher that accepts a task does not always fire.
local function Supervise()
	local now = timer.getTime()
	for groupName, mission in pairs(BMS.Missions) do
		local group = Group.getByName(groupName)
		if not group then
			BMS.Missions[groupName] = nil
			Say(mission, "battery is out of action, end of mission.")
			BMS.BuildMenu(mission.observer)
		else
			local ammoNow = CountRounds(groupName)
			local delivered = mission.ammoAtStart - ammoNow
			if delivered > mission.delivered then
				mission.delivered = delivered
				mission.lastShot = now
			end
			local sinceTask = (mission.taskBaseline or mission.ammoAtStart) - ammoNow

			if mission.delivered >= mission.requested then
				EndMission(mission, "rounds complete, " .. mission.delivered .. " away on "
					.. mission.label .. ", end of mission, out.")
			elseif ammoNow == 0 then
				EndMission(mission, "rounds complete, " .. mission.delivered
					.. " away, launcher empty, end of mission, out.")
			elseif sinceTask == 0 and now - mission.tasked > BMS.LaunchTimeoutSeconds then
				if mission.delivered == 0 then
					EndMission(mission, "unable to fire on " .. mission.label
						.. ", check the target is outside minimum range and in the open, end of mission, out.")
				else
					EndMission(mission, mission.delivered .. " of " .. mission.requested
						.. " rounds away on " .. mission.label
						.. ", launcher will not fire the rest, end of mission, out.")
				end
			elseif sinceTask > 0 and now - (mission.lastShot or mission.tasked) > BMS.RoundGapSeconds then
				-- Rounds are still on the rail with the salvo stalled. Re-issue the
				-- order before giving up: some launchers drop the task after the
				-- first round.
				if mission.retasks < BMS.MaxRetasks then
					mission.retasks = mission.retasks + 1
					TaskBattery(mission)
				else
					EndMission(mission, mission.delivered .. " of " .. mission.requested
						.. " rounds away on " .. mission.label .. ", end of mission, out.")
				end
			end
		end
	end
	return timer.getTime() + 10
end
timer.scheduleFunction(Supervise, nil, timer.getTime() + 10)

----- Radio menu -----

local function BatteryStatus(unitName)
	local unit = Unit.getByName(unitName)
	if not unit then
		return
	end
	local coalitionId = unit:getCoalition()
	local lines = {}
	for groupName, battery in pairs(BMS.Batteries) do
		local group = Group.getByName(groupName)
		if group and group:getCoalition() == coalitionId then
			local state
			local mission = BMS.Missions[groupName]
			if mission then
				state = "engaged: " .. mission.delivered .. "/" .. mission.requested .. " on " .. mission.label
			elseif BMS.Cooldowns[groupName] and timer.getTime() < BMS.Cooldowns[groupName] then
				state = "reloading, " .. (math.floor((BMS.Cooldowns[groupName] - timer.getTime()) / 60) + 1) .. " min"
			else
				state = "ready"
			end
			table.insert(lines, battery.callsign .. ": " .. CountRounds(groupName) .. " round(s), "
				.. NM(battery.minRange) .. "-" .. NM(MaxRangeFor(groupName))
				.. " NM, " .. state)
		end
	end
	if #lines == 0 then
		table.insert(lines, "No ballistic missile batteries available.")
	end
	trigger.action.outTextForGroup(unit:getGroup():getID(), table.concat(lines, "\n"), 20)
end

function BMS.BuildMenu(unitName)
	local observer = BMS.Observers[unitName]
	local unit = Unit.getByName(unitName)
	if not observer or not observer.id or not unit then
		return
	end
	local groupID = observer.id
	local coalitionId = unit:getCoalition()

	-- Remove by the path DCS handed back, never by name. A non-table path
	-- resolves to the menu root, which wipes every other script's items too.
	if observer.rootPath then
		missionCommands.removeItemForGroup(groupID, observer.rootPath)
	end
	local root = missionCommands.addSubMenuForGroup(groupID, BMS.MenuName)
	observer.rootPath = root

	-- Rebuilding is how a player picks up markers placed since the menu was drawn.
	missionCommands.addCommandForGroup(groupID, "Refresh target list", root, BMS.BuildMenu, unitName)
	missionCommands.addCommandForGroup(groupID, "Battery status", root, BatteryStatus, unitName)

	local marks = BMS.Marks[coalitionId] or {}
	local first = math.max(1, #marks - BMS.MaxMarksListed + 1)

	local batteries = 0
	for groupName, battery in pairs(BMS.Batteries) do
		local group = Group.getByName(groupName)
		if group and group:getCoalition() == coalitionId then
			local available = CountRounds(groupName)
			if available > 0 then
				batteries = batteries + 1
				-- Use the path returned by DCS rather than rebuilding it from the
				-- display name, so two batteries sharing a name cannot collide.
				local batteryMenu = missionCommands.addSubMenuForGroup(groupID,
					battery.callsign .. " (" .. available .. ")", root)
				local mission = BMS.Missions[groupName]
				if mission then
					missionCommands.addCommandForGroup(groupID,
						"Engaged: " .. mission.delivered .. "/" .. mission.requested .. " on " .. mission.label,
						batteryMenu, BMS.BuildMenu, unitName)
					missionCommands.addCommandForGroup(groupID, "Check fire", batteryMenu, CheckFire, {unitName, groupName})
				elseif #marks == 0 then
					missionCommands.addCommandForGroup(groupID, "Mark a target on the F10 map first", batteryMenu, BMS.BuildMenu, unitName)
				else
					local maxRounds = math.min(available, BMS.MaxRoundsPerMission)
					for i = first, #marks do
						local mark = marks[i]
						local markMenu = missionCommands.addSubMenuForGroup(groupID, MarkLabel(mark), batteryMenu)
						for qty = 1, maxRounds do
							local label = qty .. " round(s)"
							if qty > 1 and qty == available then
								label = label .. " - full salvo"
							end
							missionCommands.addCommandForGroup(groupID, label, markMenu, Fire, {unitName, groupName, mark.idx, qty})
						end
					end
				end
			end
		end
	end

	if batteries == 0 then
		missionCommands.addCommandForGroup(groupID, "No ballistic missile batteries available", root, BMS.BuildMenu, unitName)
	end
end

----- Launcher readiness -----

-- A launcher left on a GREEN alarm state only starts its (600s, for the 9K720)
-- power-up when it is first tasked, which reads as a lost fire mission. Wake up
-- the batteries belonging to a coalition that has players in it, so they are hot
-- by the time anyone calls a strike. Enemy launchers are left as generated.
local function PreHeat(coalitionId)
	if BMS.PreHeated[coalitionId] then
		return
	end
	BMS.PreHeated[coalitionId] = true
	for groupName, _ in pairs(BMS.Batteries) do
		local group = Group.getByName(groupName)
		if group and group:getCoalition() == coalitionId then
			local controller = group:getController()
			if BMS.PreHeatLaunchers then
				controller:setOption(AI.Option.Ground.id.ALARM_STATE, AI.Option.Ground.val.ALARM_STATE.RED)
			end
			if BMS.ReserveForPlayers then
				-- Retribution can give missile sites a pre-planned fire task.
				-- Clear it on our own side so the AI does not spend the rounds
				-- the players are being offered.
				controller:resetTask()
			end
		end
	end
	env.info("DCSRetribution|Ballistic Missile Strike plugin - Prepared launchers for coalition " .. coalitionId)
end

----- Observer tracking -----

-- A slot reports no unit until a player occupies it, so the menu has to be
-- built on a poll rather than once at mission start.
local function CheckObservers()
	for unitName, observer in pairs(BMS.Observers) do
		local unit = Unit.getByName(unitName)
		if unit and observer.active == nil then
			observer.active = true
			observer.id = unit:getGroup():getID()
			if BMS.PreHeatLaunchers or BMS.ReserveForPlayers then
				PreHeat(unit:getCoalition())
			end
			BMS.BuildMenu(unitName)
		elseif unit == nil then
			observer.active = nil
		end
	end
	return timer.getTime() + 5
end
timer.scheduleFunction(CheckObservers, nil, timer.getTime() + 2)
