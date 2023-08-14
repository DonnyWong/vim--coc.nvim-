return {
	{
		"nvim-tree/nvim-tree.lua",
		keys = { "tt" },
		config = function()
			require("nvim-tree").setup({
			sort_by = "case_sensitive",
			  view = {
			    width = 30,
			  },
			  renderer = {
			    group_empty = true,
			  },
			  filters = {
			    dotfiles = true,
			  },
			})
			vim.cmd("noremap tt :NvimTreeToggle<CR>")
		end
	}
}
