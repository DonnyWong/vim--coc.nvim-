return {
	{
		"shellRaining/hlchunk.nvim",
		event = "CursorMoved",
		config = function()
			vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, { pattern = "*", command = "EnableHL", })
			require('hlchunk').setup({
				chunk = {
					enable = true,
					notify = false,
					use_treesitter = true,
					style = {
						{ fg = "#9ae204" },
					},
				},
				indent = {
					chars = { "│", "¦", "┆", "┊", },
					use_treesitter = false,
					style = {
						{ fg = "#00a1f9" },
						{ fg = "#ffc400" },
						{ fg = "#805bb5" },
						{ fg = "#00ddef" },
					},
				},
				blank = {
					enable = false,
				},
				line_num = {
					use_treesitter = true,
				},
			})
		end
	},
	-- {
	-- 	"lukas-reineke/indent-blankline.nvim",
	-- 	opts = {
	-- 		show_current_context = true,
	-- 		show_current_context_start = false,
	-- 	}
	-- },
}
