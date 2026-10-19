local unitPayloads = {
	["name"] = "OH-58D",
	["payloads"] = {
		[1] = {
			["name"] = "CAS",
			["pylons"] = {
				[1] = {
					["CLSID"] = "oh-58-brauning",
					["num"] = 1,
				},
				[2] = {
					["CLSID"] = "AGM114x2_OH_58",
					["num"] = 2,
				},
			},
			["tasks"] = {
				[1] = 16,
			},
		},
		[2] = {
			["name"] = "CAP",
			["pylons"] = {
				[1] = {
					["CLSID"] = "AGM114x2_OH_58",
					["num"] = 1,
				},
				[2] = {
					["CLSID"] = "AGM114x2_OH_58",
					["num"] = 2,
				},
			},
			["tasks"] = {
				[1] = 16,
			},
		},
	},
	["unitType"] = "OH-58D",
}
return unitPayloads
