return {
	{
		"lewis6991/gitsigns.nvim",
		event = "BufRead",
		config = function()
			require('gitsigns').setup({
				signs = {
					signs        = {
						add          = { text = '┃' },
						change       = { text = '░' },
						delete       = { text = '_' },
						topdelete    = { text = '▔' },
						changedelete = { text = '▒' },
						untracked    = { text = '┆' },
					},
					signcolumn   = true, -- Toggle with `:Gitsigns toggle_signs`
					numhl        = true, -- Toggle with `:Gitsigns toggle_numhl`
					linehl       = true, -- Toggle with `:Gitsigns toggle_linehl`
					word_diff    = true, -- Toggle with `:Gitsigns toggle_word_diff`
					watch_gitdir = {
						follow_files = true
					},
					auto_attach  = true,
				},
			})
			vim.keymap.set("n", "<leader>g-", ":Gitsigns prev_hunk<CR>", { noremap = true, silent = true })
			vim.keymap.set("n", "<leader>g=", ":Gitsigns next_hunk<CR>", { noremap = true, silent = true })
			vim.keymap.set("n", "<leader>gb", ":Gitsigns blame_line<CR>", { noremap = true, silent = true })
			vim.keymap.set("n", "<leader>gr", ":Gitsigns reset_hunk<CR>", { noremap = true, silent = true })
			vim.keymap.set("n", "H", ":Gitsigns preview_hunk_inline<CR>", { noremap = true, silent = true })
		end
	},
	{
		"kdheepak/lazygit.nvim",
		keys = { "<c-g>" },
		config = function()
			vim.g.lazygit_floating_window_scaling_factor = 1.0
			vim.g.lazygit_floating_window_winblend = 0
			vim.g.lazygit_use_neovim_remote = true
			vim.keymap.set("n", "<c-g>", ":LazyGit<CR>", { noremap = true, silent = true })
		end
	},
	-- {
		-- 	"APZelos/blamer.nvim",
		-- 	config = function()
			-- 		vim.g.blamer_enabled = true
			-- 		vim.g.blamer_relative_time = true
			-- 	end
			-- }
		}
