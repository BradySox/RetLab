local unitPayloads = {
	["name"] = "SA342Mistral",
	["payloads"] = {
		[1] = {
			["name"] = "CAP",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{MBDA_MistralD}",
					["num"] = 1,
				},
				[2] = {
					["CLSID"] = "{MBDA_MistralG}",
					["num"] = 2,
				},
				[3] = {
					["CLSID"] = "{MBDA_MistralD}",
					["num"] = 3,
				},
				[4] = {
					["CLSID"] = "{MBDA_MistralG}",
					["num"] = 4,
				},
				[5] = {
					["CLSID"] = "{IR_Deflector}",
					["num"] = 6,
				},
				[6] = {
					["CLSID"] = "{FAS}",
					["num"] = 5,
				},
			},
			["tasks"] = {
				[1] = 18,
			},
		},
	},
	["tasks"] = {
	},
	["unitType"] = "SA342Mistral",
}
return unitPayloads
