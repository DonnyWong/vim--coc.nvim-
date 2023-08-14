return {
	'akinsho/toggleterm.nvim',
	event = 'VeryLazy',
	keys = { "F" },
	config = function()
		require('toggleterm').setup({
			vim.cmd([[noremap F :ToggleTerm<CR>]]),
			direction = 'float',
		})
	end
}
