-- vim.opt.termguicolors = true
vim.o.ttyfast = true
--自动切换工作目录
vim.o.autochdir = true
vim.o.exrc = true
--是否启用安全模式
vim.o.secure = false
--显示行号
-- vim.o.number = true
-- vim.o.relativenumber = true
--高亮光标所在行
vim.o.cursorline = true
--是否将制表符（Tab）自动转换为空格
vim.o.expandtab = false
--制表符（Tab）占用空格数
vim.o.tabstop = 4
--缩进占用空格数
vim.o.smarttab = true
vim.o.shiftwidth = 4
vim.o.softtabstop = 4
--自动缩进
vim.o.autoindent = true
--是否显示可见字符，如空格、制表符等的特殊表示
--vim.o.list = true
--vim.o.listchars = 'tab:|\\ ,trail:▫'
--设置在光标距离屏幕顶部和底部一定行数
vim.o.scrolloff = 4
--设置在键盘键入过程中，判断键入操作是否超时的时间阈值
vim.o.ttimeoutlen = 0
--设置键盘按键的等待时间，以确定是否将已输入的按键序列视为键盘映射或键盘命令
vim.o.timeout = false
--控制文本是否自动换行显示
vim.o.wrap = true
--设置自动换行时的文本宽度阈值
vim.o.textwidth = 0
--设置代码折叠的方法
vim.o.foldmethod = 'indent'
--设置默认的代码折叠层级
vim.o.foldlevel = 99
--控制代码折叠功能的启用或禁用
vim.o.foldenable = true
--设置打开文件后默认的代码折叠层级
vim.o.foldlevelstart = 99
--控制自动格式化和文本处理的行为，t在新行上自动插入当前行的缩进，并且在}之后添加额外的缩进，c自动在注释标记后继续注释文本
vim.o.formatoptions = vim.o.formatoptions:gsub('tc', '')
--控制新打开的分割窗口是否位于当前窗口的右侧
vim.o.splitright = true
--控制新打开的分割窗口是否位于当前窗口的下方
vim.o.splitbelow = true
--是否在命令行底部显示当前的编辑模式
vim.o.showmode = true
--搜索操作是否忽略大小写
vim.o.ignorecase = true
--搜索操作时自动切换搜索的大小写敏感性
vim.o.smartcase = true
--控制 Vim 是否在执行某些操作时显示已完成消息
vim.o.shortmess = vim.o.shortmess .. 'c'
--在执行替换、查找和查找/替换操作时，实时显示操作结果的预览
vim.o.inccommand = 'split'
--设置在自动完成补全过程中的补全选项的行为
vim.o.completeopt = 'longest,preview'
vim.o.completeopt = 'menu,preview'
--是否延迟重绘屏幕上的内容
-- vim.o.lazyredraw = true
-- 控制是否在发出响铃（bell）信号时显示可视提示而不是声音
vim.o.visualbell = true
--编辑窗口中设置一条垂直的色块线，以标识特定的列位置
-- vim.o.colorcolumn = '100'
--控制自动保存文件和触发自动命令的时间间隔
vim.o.updatetime = 100
--允许光标停留在文本的空白区域内，但不能在实际字符的位置停留
vim.o.virtualedit = 'block'
--共享剪贴板
vim.o.clipboard = 'unnamed'
--在底部显示，当前键入的指令
vim.o.showcmd = true
--自动保存
vim.o.autowrite = true
--在处理未保存或只读文件的时候，弹出确认
vim.o.confirm = true
--编码设置
vim.o.encoding = 'utf-8'
vim.o.fileencodings = "ucs-bom,utf-8,gb18030,gbk,gb2312,cp936"
--语言设置
vim.o.langmenu = 'zh_CN.UTF-8'

vim.cmd([[
silent !mkdir -p $HOME/.config/nvim/tmp/backup
silent !mkdir -p $HOME/.config/nvim/tmp/undo
"silent !mkdir -p $HOME/.config/nvim/tmp/sessions
set backupdir=$HOME/.config/nvim/tmp/backup,.
set directory=$HOME/.config/nvim/tmp/backup,.
if has('persistent_undo')
	set undofile
	set undodir=$HOME/.config/nvim/tmp/undo,.
endif
]])

vim.api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, { pattern = "*.md", command = "setlocal spell", })
vim.api.nvim_create_autocmd("BufEnter", { pattern = "*", command = "silent! lcd %:p:h", })

vim.cmd([[au BufReadPost * if line("'\"") > 1 && line("'\"") <= line("$") | exe "normal! g'\"" | endif]])

