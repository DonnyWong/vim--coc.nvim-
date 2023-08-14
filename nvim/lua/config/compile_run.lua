local split = function()
	vim.cmd("set splitbelow")
	vim.cmd("sp")
	vim.cmd("res -5")
end
local compileRun = function()
	vim.cmd("w")
	-- check file type
	local ft = vim.bo.filetype
	if ft == "dart" then
		vim.cmd(":FlutterRun -d " .. vim.g.flutter_default_device .. " " .. vim.g.flutter_run_args .. "<CR>")
	elseif ft == "markdown" then
		vim.cmd(":InstantMarkdownPreview")
	elseif ft == 'lua' then
		split()
		vim.cmd("term luajit %")
	elseif ft == 'python' then
		split()
		vim.cmd("term time python %")
	elseif ft == 'c' then
		split()
		vim.cmd("term gcc -std=c17 % -o %< && time ./%<")
	elseif ft == 'cpp' then
		split()
		vim.cmd("term g++ -std=c++20 % -o %< && time ./%<")
	elseif ft == 'sh' then
		split()
		vim.cmd("term bash %")
	elseif ft == 'java' then
		split()
		vim.cmd("term javac % && time java %<")
	elseif ft == 'html' then
		split()
		vim.cmd("term google-chrome % &")

	end
end

vim.keymap.set('n', 'r', compileRun, {silent = true })

