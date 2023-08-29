return {
	'akinsho/toggleterm.nvim',
	keys = { "F" },
	config = function()
		require('toggleterm').setup({
			vim.cmd([[noremap F :ToggleTerm<CR>]]),
			direction = 'float',
		})
	end
}
