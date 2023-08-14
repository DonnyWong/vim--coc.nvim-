return {
	{
		"github/copilot.vim",
		config = function()
			vim.g.copilot_enabled = true
			vim.api.nvim_set_keymap('n', 'C', ':Copilot<CR>', { silent = true })
		end
	}
	-- {
	-- 	"Exafunction/codeium.vim",
	-- 	config = function()
	-- 		vim.g.codeium_disable_bindings = 1
	-- 		vim.keymap.set('i', '<C-c>', function() return vim.fn['codeium#Accept']() end, { expr = true })
	-- 		vim.keymap.set('i', '<c-[>', function() return vim.fn['codeium#CycleCompletions'](1) end, { expr = true })
	-- 		vim.keymap.set('i', '<c-x>', function() return vim.fn['codeium#CycleCompletions'](-1) end, { expr = true })
	-- 		-- vim.keymap.set('i', '<c-x>', function() return vim.fn['codeium#Clear']() end, { expr = true })
	-- 	end
	-- }
	-- {
	-- 	"jcdickinson/codeium.nvim",
	-- 	dependencies = {
	-- 		"nvim-lua/plenary.nvim",
	-- 		"hrsh7th/nvim-cmp",
	-- 	},
	-- 	config = function()
	-- 		require("codeium").setup({
	-- 		})
	-- 	end
	-- },
}
