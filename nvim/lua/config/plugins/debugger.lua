return {
	{
		"mfussenegger/nvim-dap",
		keys = { "<leader>'t" },
		dependencies = {
			{
				"ravenxrz/DAPInstall.nvim",
				config = function()
					local dap_install = require("dap-install")
					dap_install.setup({
						installation_path = vim.fn.stdpath("data") .. "/dapinstall/",
					})
				end
			},
			"theHamsta/nvim-dap-virtual-text",
			"rcarriga/nvim-dap-ui",
			"nvim-dap-virtual-text",
			"nvim-telescope/telescope-dap.nvim",
		},
		config = function()
			local dap = require("dap")
			local dapui = require("dapui")
			dapui.setup({
				element_mappings = {
					scopes = {
						edit = "e",
						repl = "r",
					},
					watches = {
						edit = "e",
						repl = "r",
					},
					stacks = {
						open = "g",
					},
					breakpoints = {
						open = "g",
						toggle = "b",
					},
				},

				layouts = {
					{
						elements = {
							"scopes",
							"stacks",
							"breakpoints",
							"watches",
						},
						size = 0.2, -- 40 columns
						position = "left",
					},
					{
						elements = {
							"repl",
						},
						size = 0.25, -- 25% of total lines
						position = "bottom",
					},
					{
						elements = {
							"console",
						},
						size = 0.2,
						position = "right",
					},
				},

				floating = {
					max_height = nil, -- These can be integers or a float between 0 and 1.
					max_width = nil, -- Floats will be treated as percentage of your screen.
					border = "rounded", -- Border style. Can be "single", "double" or "rounded"
					mappings = {
						close = { "q", "<Esc>" },
					},
				},
			})
			require("nvim-dap-virtual-text").setup({
				enabled = true,
				enable_commands = true,
				highlight_changed_variables = true,
				highlight_new_as_changed = false,
				show_stop_reason = true,
				commented = false,
				only_first_definition = true,
				all_references = false,
				filter_references_pattern = '<module',
				virt_text_pos = 'eol',
				all_frames = false,
				virt_lines = false,
				virt_text_win_col = nil
			})

			local m = { noremap = true }
			vim.keymap.set("n", "<leader>'q", ":Telescope dap<CR>", m)
			vim.keymap.set("n", "<leader>'t", dap.toggle_breakpoint, m)
			vim.keymap.set("n", "<leader>'n", dap.continue, m)
			vim.keymap.set("n", "<leader>'s", dap.terminate, m)
			vim.keymap.set("n", "<leader>'u", dapui.toggle, m)
			vim.keymap.set("n", "<leader>'c", dapui.close, m)
			vim.keymap.set("n", "<leader>'d", dapui.open, m)


			vim.api.nvim_set_hl(0, 'DapBreakpoint', { ctermbg = 0, fg = '#993939', bg = '#31353f' })
			vim.api.nvim_set_hl(0, 'DapLogPoint', { ctermbg = 0, fg = '#61afef', bg = '#31353f' })
			vim.api.nvim_set_hl(0, 'DapStopped', { ctermbg = 0, fg = '#98c379', bg = '#31353f' })


			local dap_breakpoint = {
				error = {
					text = "🛑",
					texthl = "DapBreakpoint",
					linehl = "DapBreakpoint",
					numhl = "DapBreakpoint",
				},
				condition = {
					text = '󰟃',
					texthl = 'DapBreakpoint',
					linehl = 'DapBreakpoint',
					numhl = 'DapBreakpoint',
				},
				rejected = {
					text = "󰃤",
					texthl = "DapBreakpint",
					linehl = "DapBreakpoint",
					numhl = "DapBreakpoint",
				},
				logpoint = {
					text = '',
					texthl = 'DapLogPoint',
					linehl = 'DapLogPoint',
					numhl = 'DapLogPoint',
				},
				stopped = {
					text = '󰜴',
					texthl = 'DapStopped',
					linehl = 'DapStopped',
					numhl = 'DapStopped',
				},
			}
			vim.fn.sign_define('DapBreakpoint', dap_breakpoint.error)
			vim.fn.sign_define('DapBreakpointCondition', dap_breakpoint.condition)
			vim.fn.sign_define('DapBreakpointRejected', dap_breakpoint.rejected)
			vim.fn.sign_define('DapLogPoint', dap_breakpoint.logpoint)
			vim.fn.sign_define('DapStopped', dap_breakpoint.stopped)

			dap.listeners.after.event_initialized["dapui_config"] = function()
				dapui.open()
			end

			dap.listeners.before.event_terminated["dapui_config"] = function()
				dapui.close()
			end

			dap.listeners.before.event_exited["dapui_config"] = function()
				dapui.close()
			end

			require("config.dap.cpp")
			require("config.dap.python")
		end
	}
}
