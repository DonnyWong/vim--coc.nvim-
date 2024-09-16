vim.g.mapleader = " "

local mode_n = { "n" }
local mode_nv = { "n", "v" }
local mode_v = { "v" }
local mode_i = { "i" }
local nmappings = {
	{ from = "Y",            to = "\"+y",                                                   mode = mode_v },
	--删除Mark标记后面输入要删除的标记
	{ from = "dm",           to = ":delmarks",                                              mode = mode_n },
	--显示标记 加上标记跳转到标记处
	{ from = "mk",           to = ":marks<CR>",                                             mode = mode_n },

	-- Movement
	{ from = "K",            to = "5k",                                                     mode = mode_nv },
	{ from = "J",            to = "5j",                                                     mode = mode_nv },

	-- Useful actions
	{ from = ",.",           to = "%",                                                      mode = mode_nv },
	{ from = "<c-y>",        to = "<ESC>A {}<ESC>i<CR><ESC>ko",                             mode = mode_i },
	{ from = "<c-a>",        to = "<ESC>A",                                                 mode = mode_i },

	-- Window & splits
	{ from = "\\",           to = "<C-w><C-w>", },
	{ from = "qf",           to = "<C-w>o", },
	{ from = "s",            to = "<nop>", },
	{ from = "sk",           to = ":set nosplitbelow<CR>:split<CR>:set splitbelow<CR>", },
	{ from = "sj",           to = ":set splitbelow<CR>:split<CR>", },
	{ from = "sh",           to = ":set nosplitright<CR>:vsplit<CR>:set splitright<CR>", },
	{ from = "sl",           to = ":set splitright<CR>:vsplit<CR>", },
	{ from = "<LEADER>k",    to = ":res +5<CR>", },
	{ from = "<LEADER>j",    to = ":res -5<CR>", },
	{ from = "<LEADER>h",    to = ":vertical resize-5<CR>", },
	{ from = "<LEADER>l",    to = ":vertical resize+5<CR>", },

	-- Tab management
	{ from = "tu",           to = ":tabe ", },
	{ from = "tU",           to = ":tab split<CR>", },
	{ from = "tn",           to = ":-tabnext<CR>", },
	{ from = "ti",           to = ":+tabnext<CR>", },
	{ from = "tmn",          to = ":-tabmove<CR>", },
	{ from = "tmi",          to = ":+tabmove<CR>", },

	-- Other
	--Y 全选
	{ from = "Y",            to = "ggVGy" },
	--按<Leader>B显示编辑过的文件
	--按q退出上下翻阅然后按相应的数字选择编辑文件
	{ from = "<LEADER>b",    to = ":browse oldfiles<CR>",                                   mode = mode_n },
	{ from = "<leader><CR>", to = ":nohlsearch<CR>" },
	{ from = "P",            to = ":reg<CR>",                                               mode = mode_n },
	--可视模式按 * 或 # 搜索当前选择
	{ from = "<silent> *",   to = ":<C-u>call VisualSelection('', '')<CR>/<C-R>=@/<CR><CR>" },
	{ from = "<silent> #",   to = ":<C-u>call VisualSelection('', '')<CR>/<C-R>=@/<CR><CR>" },

}

for _, mapping in ipairs(nmappings) do
	vim.keymap.set(mapping.mode or "n", mapping.from, mapping.to, { noremap = true })
end

-- 自动补全
vim.api.nvim_set_keymap('i', '(', '()<ESC>i', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', ')', '<c-r>=ClosePair(\')\')<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '{', '{}<ESC>i', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '{<CR>', '{<CR>}<ESC>O', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '[', '[]<ESC>i', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', ']', '<c-r>=ClosePair(\']\')<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '"', '""<ESC>i', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', "'", "''<ESC>i", { noremap = true, silent = true })

-- 定义括号匹配函数
function ClosePair(char)
	if vim.fn.getline('.')[vim.fn.col('.') - 1] == char then
		return "<Right>"
	else
		return char
	end
end

-- 定义自定义命令 "W" 来保存文件
vim.cmd([[command! -nargs=0 W execute 'w !sudo tee % > /dev/null' | edit!]])

-- 让配置变更立即生效
vim.api.nvim_exec([[
augroup auto_reload_config
autocmd!
autocmd BufWritePost $MYVIMRC luafile $MYVIMRC
augroup END
]], false)


-- 设置文件头
vim.cmd([[
"新建.c,.h,.sh,.java文件，自动插入文件头
autocmd BufNewFile *.cpp,*.[ch],*.sh,*.py,*.java exec ":call SetTitle()"
""定义函数SetTitle，自动插入文件头
func SetTitle()
"如果文件类型为.sh文件
if expand("%:e") == 'sh'
	call setline(1,"\#!/bin/bash")
	call append(line("."),"\#########################################################################")
	call append(line(".")+1, "\# File Name:".expand("%"))
	call append(line(".")+2, "\# Author:Donny")
	call append(line(".")+3, "\# Email:wdm666666@gmail.com")
	call append(line(".")+4, "\# Created Time: ".strftime("%c"))
	call append(line(".")+5, "\#########################################################################")
	call append(line(".")+6, "")
elseif expand("%:e") == 'py'
	call setline(1,"\#!/usr/bin/env python")
	call append(line("."),"\#########################################################################")
	call append(line(".")+1, "\# File Name: ".expand("%"))
	call append(line(".")+2, "\# Author:Donny")
	call append(line(".")+3, "\# Email:wdm666666@gmail.com")
	call append(line(".")+4, "\# Created Time: ".strftime("%c"))
	call append(line(".")+5, "\#########################################################################")
	call append(line(".")+6, "")
else
	call setline(1,"/*#########################################################################")
	call append(line("."), "\# File Name: ".expand("%"))
	call append(line(".")+1, "\# Author:狌狌编程")
	call append(line(".")+2, "\# Contact:xxcoding")
	call append(line(".")+3, "\# Created Time: ".strftime("%c"))
	call append(line(".")+4, "#########################################################################*/")
	call append(line(".")+5, "")
	endif
	if expand("%:e") == 'cpp'
		call append(line(".")+6, "#include <bits/stdc++.h>")
		call append(line(".")+7, "#define endl '\\n'")
		call append(line(".")+8, "typedef long long ll;")
		call append(line(".")+9, "using std::cin;")
		call append(line(".")+10, "using std::cout;")
		call append(line(".")+11, "const int MAXN = 1e5 + 10;")
		call append(line(".")+12, "")
		call append(line(".")+13, "void solve();")
		call append(line(".")+14, "int main(int argc, char *argv[]) {")
		call append(line(".")+15, "	std::ios::sync_with_stdio(false);")
		call append(line(".")+16, "	cin.tie(0);")
		call append(line(".")+17, "	cout.tie(0);")
		call append(line(".")+18, "")
		call append(line(".")+19, "	ll _T = 1;")
		call append(line(".")+20, "	cin >> _T;")
		call append(line(".")+21, "	while (_T--) {")
		call append(line(".")+22, "		solve();")
		call append(line(".")+23, "	}")
		call append(line(".")+24, "")
		call append(line(".")+25, "	return 0;")
		call append(line(".")+26, "}")
		call append(line(".")+27, "")
		call append(line(".")+28, "void solve(){")
		call append(line(".")+29, "}")

		endif
		if expand("%:e") == 'c'
			call append(line(".")+6, "#include<stdio.h>")
			call append(line(".")+7, "")
			endif
			"新建文件后，自动定位到文件末尾
			endfunc
			autocmd BufNewFile * normal G
			]])
