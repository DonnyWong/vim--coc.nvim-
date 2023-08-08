return {
	"voldikss/vim-floaterm",
	keys = { "F" },
	config = function()
		vim.cmd([[
		" noremap F :FloatermNew<CR>
		" tnoremap F <C-\><C-n>:FloatermNew<CR>
		nnoremap FD :FloatermPrev<CR>
		tnoremap FD <C-\><C-n>:FloatermPrev<CR>
		nnoremap FG :FloatermNew fzf<CR>

		noremap F :call CompileRunFGcc()<CR>
		func! CompileRunFGcc()
		exec "w"
		if &filetype == 'c'
			:FloatermNew! gcc -std=c17 % -o %< && time ./%<
		elseif &filetype == 'cpp'
			:FloatermNew! g++ -std=c++20 % -o %< && time ./%<
		elseif &filetype == 'java'
			:FloatermNew! javac % && time java %<
		elseif &filetype == 'sh'
			:FloatermNew! time sh %
		elseif &filetype == 'python'
			:FloatermNew! time python %
			endif
			endfunc]])
		end
	}
