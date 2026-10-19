local unitPayloads = {
	["name"] = "SA342L",
	["payloads"] = {
		[1] = {
			["name"] = "CAP",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{SA342_Mistral_L2}",
					["num"] = 2,
				},
				[2] = {
					["CLSID"] = "{IR_Deflector}",
					["num"] = 4,
				},
				[3] = {
					["CLSID"] = "{FAS}",
					["num"] = 3,
				},
				[4] = {
					["CLSID"] = "{SA342_Mistral_R2}",
					["num"] = 1,
				},
			},
			["tasks"] = {
				[1] = 31,
			},
		},
		[2] = {
			["name"] = "CAS",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{TELSON8_SNEBT257}",
					["num"] = 2,
				},
				[2] = {
					["CLSID"] = "{IR_Deflector}",
					["num"] = 4,
				},
				[3] = {
					["CLSID"] = "{FAS}",
					["num"] = 3,
				},
				[4] = {
					["CLSID"] = "{TELSON8_SNEBT257}",
					["num"] = 1,
				},
			},
			["tasks"] = {
				[1] = 31,
			},
		},
	},
	["tasks"] = {
	},
	["unitType"] = "SA342L",
}
return unitPayloads
