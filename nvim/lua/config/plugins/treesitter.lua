return {
	"nvim-treesitter/nvim-treesitter",
	-- event = { "BufReadPost", "BufNewFile" },
	build = ":TSUpdate",

	config = function()
		require("nvim-treesitter.configs").setup({
			ensure_installed = { "c", "cpp", "cmake", "java", "rust", "lua", "vim", "vimdoc", "query", "python", "json", "markdown" },
			auto_install = true,
		})
	end
}
