local configureKeybinds = function()
	vim.api.nvim_create_autocmd('LspAttach', {
		desc = 'LSP actions',
		callback = function(event)
			local opts = { buffer = event.buf, noremap = true, nowait = true }

			vim.keymap.set('n', '<leader>h', vim.lsp.buf.hover, opts)
			vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
			vim.keymap.set('n', 'gD', ':tab sp<CR><cmd>lua vim.lsp.buf.definition()<cr>', opts)
			vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
			vim.keymap.set('n', 'go', vim.lsp.buf.type_definition, opts)
			vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
			vim.keymap.set('i', '<c-f>', vim.lsp.buf.signature_help, opts)
			vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts)
			-- vim.keymap.set({ 'n', 'x' }, '<leader>f', function() vim.lsp.buf.format({ async = true }) end, opts)
			vim.keymap.set('n', '<leader>aw', vim.lsp.buf.code_action, opts)
			vim.keymap.set('n', '<leader>-', vim.diagnostic.goto_prev, opts)
			vim.keymap.set('n', '<leader>=', vim.diagnostic.goto_next, opts)
		end
	})
end

local configureDocAndSignature = function()
	vim.lsp.handlers["textDocument/signatureHelp"] = vim.lsp.with(
	vim.lsp.handlers.signature_help, {
		silent = true,
		focusable = false,
		border = "rounded",
	}
	)
	local group = vim.api.nvim_create_augroup("lsp_diagnostics_hold", { clear = true })
	vim.api.nvim_create_autocmd({ "CursorHold" }, {
		pattern = "*",
		callback = function()
			vim.diagnostic.open_float(0, {
				scope = "cursor",
				focusable = false,
				close_events = {
					"CursorMoved",
					"CursorMovedI",
					"BufHidden",
					"InsertCharPre",
					"WinLeave",
				},
			})
		end,
		group = group,
	})
end

return {
	{
		'weilbith/nvim-code-action-menu',
		cmd = 'CodeActionMenu',
	},
	{
		"folke/trouble.nvim",
		keys = { "<leader>T" },
		opts = {
			use_diagnostic_signs = true,
			action_keys = {
				close = "<esc>",
				previous = "u",
				next = "e"
			},
		},
		config = function()
			vim.keymap.set('n', '<leader>T', ':Trouble<cr>', opts)
		end
	},
	{
		'VonHeikemen/lsp-zero.nvim',
		event = { "BufReadPre", "BufNewFile" },
		dependencies = {
			{ 'neovim/nvim-lspconfig' },
			{
				--mason clangd 设置路径：/Users/donny/.local/share/nvim/mason/packages/clangd/clangd_16.0.2/lib/clang/16/include
				'williamboman/mason.nvim',
				config = function()
					require("mason").setup({
						ui = {
							icons = {
								package_installed = "✓",
								package_pending = "➜",
								package_uninstalled = "✗"
							}
						}
					})
				end
			},
			{
				'williamboman/mason-lspconfig.nvim',
				config = function()
					require("mason-lspconfig").setup({
						ensure_installed = {
							"clangd",
							"pyright",
							"jsonls",
							"jdtls",
							"lua_ls",
							"cmake",
						},
					})
				end
			},
			{ 'hrsh7th/cmp-nvim-lsp' },
			{
				'j-hui/fidget.nvim',
				tag = "legacy"
			},
			-- "folke/neodev.nvim",
			-- "ray-x/lsp_signature.nvim",
			-- {
			-- 	"lvimuser/lsp-inlayhints.nvim",
			-- 	branch = "anticonceal",
			-- },
		},

		config = function()
			local lsp = require('lsp-zero').preset({})


			lsp.on_attach(function(client, bufnr)
				lsp.default_keymaps({ buffer = bufnr })
				client.server_capabilities.semanticTokensProvider = nil
				require("config.plugins.autocomplete").configfunc()
				vim.diagnostic.config({
					severity_sort = true,
					underline = true,
					signs = true,
					virtual_text = false,
					update_in_insert = false,
					float = true,
				})
			end)

			lsp.set_sign_icons({
				error = '✘',
				warn = '▲',
				hint = '⚑',
				info = '»'
			})

			lsp.set_server_config({
				on_init = function(client)
					client.server_capabilities.semanticTokensProvider = nil
				end,
			})

			lsp.format_on_save({
				format_opts = {
					-- async = false,
					-- timeout_ms = 10000,
				},
			})


			local lspconfig = require('lspconfig')

			lsp.setup()
			require("fidget").setup({})

			local lsp_defaults = lspconfig.util.default_config
			lsp_defaults.capabilities = vim.tbl_deep_extend(
			'force',
			lsp_defaults.capabilities,
			require('cmp_nvim_lsp').default_capabilities()
			)


			configureDocAndSignature()
			configureKeybinds()

			local format_on_save_filetypes = {
				dart = true,
				json = true,
				lua = true,
				python = true,
				cpp = true,
				c = true,
				rust = true,
				java = true,
				sh = true,
				cmake = true,
			}

			vim.api.nvim_create_autocmd("BufWritePre", {
				pattern = "*",
				callback = function()
					if format_on_save_filetypes[vim.bo.filetype] then
						local lineno = vim.api.nvim_win_get_cursor(0)
						vim.lsp.buf.format({ async = false })
						vim.api.nvim_win_set_cursor(0, lineno)
						-- 设置自动缩进4个宽度
						vim.api.nvim_exec([[
						:normal! mzgg=G`z
						]], false)
					end
				end,
			})
		end
	},
}
