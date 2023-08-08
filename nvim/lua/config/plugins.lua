local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
	vim.fn.system({
		"git",
		"clone",
		"--filter=blob:none",
		"https://github.com/folke/lazy.nvim.git",
		"--branch=stable", -- latest stable release
		lazypath,
	})
end
vim.opt.rtp:prepend(lazypath)
require("lazy").setup({
	--主题颜色
	require("config.plugins.colorscheme"),
	--搜索文件
	require("config.plugins.telescope"),
	--标题栏
	require("config.plugins.tabline"),
	--require("config.plugins.winbar"),
	--状态栏
	require("config.plugins.statusline"),
	--Autocomplete
	require("config.plugins.autocomplete").config,
	require("config.plugins.lspconfig"),
	require("config.plugins.snippets"),
	--通知消息
	require("config.plugins.notify"),
	--vim terminal in the floating/popup window
	require("config.plugins.floaterm"),
	--debugger
	require("config.plugins.debugger"),
	--多行注释,单行注释gcc，多行注释vgc
	require("config.plugins.comment"),
	--Change Surround examples Press cs"'
	require("config.plugins.surround"),
	--markdown
	require("config.plugins.markdown"),
	--Git
	require("config.plugins.git"),
	--缩进线
	require("config.plugins.indent"),
	--nvim-tree
	require("config.plugins.nvimtree"),
	--search
	require("config.plugins.search"),
	--UNdotree
	require("config.plugins.undo"),
	--wildmenu
	require("config.plugins.wilder"),
	--AI code
	require("config.plugins.copilot"),
},{})

require("config.compile_run")
--主题颜色设置
vim.cmd.colorscheme("smarties")
