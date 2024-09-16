return {
	-- {
	-- 	"joshdick/onedark.vim",
	-- 	lazy = true,
	-- },
	{
		"olimorris/onedarkpro.nvim",
		priority = 1000, -- Ensure it loads first

		config = function()
			require("onedarkpro").setup({
				colors = {
					fg = "#81c8ba"
				}
			})
		end,
	}
}
