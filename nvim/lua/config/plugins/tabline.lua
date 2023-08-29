return {
	'akinsho/bufferline.nvim',
	event = "BufWinEnter",
	version = "*",
	dependencies = 'nvim-tree/nvim-web-devicons',
	opts = {
		options = {
			mode = "tabs",
			diagnostics = "nvim_lsp",
			diagnostics_indicator = function(count, level, diagnostics_dict, context)
				local icon = level:match("error") and " " or " "
				return " " .. icon .. count
			end,
			indicator = {
				icon = '▎', -- this should be omitted if indicator style is not 'icon'
				-- style = 'icon' | 'underline' | 'none',
				style = "icon",
			},
			numbers = function(opts)
				local NumberIcon = {
					"❶ ", "❷ ", "❸ ", "❹ ", "❺ ", "❻ ", "❼ ", "❽ ", "❾ ", "❿ ",
				}
				return NumberIcon[tonumber(opts.ordinal)]
			end,
			show_buffer_close_icons = false,
			show_close_icon = false,
			enforce_regular_tabs = true,
			show_duplicate_prefix = false,
			tab_size = 20,
			padding = 0,
			separator_style = "thick",
		}
	}
}
