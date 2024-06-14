return {
	{
		"github/copilot.vim",
		config = function()
			vim.g.copilot_enabled = true
			vim.api.nvim_set_keymap('n', 'C', ':Copilot<CR>', { silent = true })
		end
	}
	-- {
		-- 	'codota/tabnine-nvim',
		-- 	build = "./dl_binaries.sh",
		-- 	config = function()
			-- 		require('tabnine').setup({
				-- 			disable_auto_comment = true,
				-- 			accept_keymap = "<Tab>",
				-- 			dismiss_keymap = "<C-]>",
				-- 			debounce_ms = 800,
				-- 			suggestion_color = { gui = "#808080", cterm = 244 },
				-- 			exclude_filetypes = { "TelescopePrompt" },
				-- 		})
				-- 	end
				-- }
				-- {
					-- 	"Exafunction/codeium.vim",
					-- 	config = function()
						-- 	vim.api.nvim_del_keymap('i', '<Right>') -- Disable default right arrow key
						-- 		vim.g.codeium_disable_bindings = 1
						-- 		vim.keymap.set('i', '<C-c>', function() return vim.fn['codeium#Accept']() end, { expr = true })
						-- 		vim.keymap.set('i', '<c-[>', function() return vim.fn['codeium#CycleCompletions'](1) end, { expr = true })
						-- 		vim.keymap.set('i', '<c-x>', function() return vim.fn['codeium#CycleCompletions'](-1) end, { expr = true })
						-- 		-- vim.keymap.set('i', '<c-x>', function() return vim.fn['codeium#Clear']() end, { expr = true })
						-- 	end
						-- }
						-- {
							-- 	"Exafunction/codeium.nvim",
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
