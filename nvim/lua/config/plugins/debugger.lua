return {
	{
		"mfussenegger/nvim-dap",
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
			dapui.setup()
			require("nvim-dap-virtual-text").setup()

			local m = { noremap = true }
			vim.keymap.set("n", "<leader>'q", ":Telescope dap<CR>", m)
			vim.keymap.set("n", "<leader>'t", dap.toggle_breakpoint, m)
			vim.keymap.set("n", "<leader>'n", dap.continue, m)
			vim.keymap.set("n", "<leader>'s", dap.terminate, m)
			vim.keymap.set("n", "<leader>'u", dapui.toggle, m)

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
		end
	}
}
