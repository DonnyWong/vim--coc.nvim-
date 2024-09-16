
# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi


# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

# >>> clangd initialize >>>
export PATH="/usr/local/clangd/bin:$PATH"                                                                                                                                                

# >>> ruby&gem initialize >>>
export PATH="/usr/local/opt/ruby/bin:$PATH"

# >>> node >>>
export PATH="/usr/local/node/bin:$PATH"


# >>> tensorflow >>>
export LIBRARY_PATH=$LIBRARY_PATH:/Library/Developer/CommandLineTools/usr/lib
export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:/Library/Developer/CommandLineTools/usr/lib


# Screen display
# figlet -w 100 cheng xu hou lazy | lolcat
cowsay -f monkey chengxuhoulazy|lolcat
# cowsay -f monkey chengxuhoulazy|~/center.sh|lolcat


# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# alias ll='colorls -l --sd'
# alias ls='colorls '
alias ls='lsd'
alias ll='lsd -l'
alias lt='lsd --tree --depth 4'
alias ly='yazi'


# VPN                                                                                                                                                                                    
alias proxy='export all_proxy=http://127.0.0.1:7890'
alias unproxy='unset all_proxy'

# export http_proxy=127.0.0.1:7890
# export https_proxy=127.0.0.1:7890


# Zinit

source "/usr/local/opt/zinit/zinit.zsh"
# source "$HOME/.local/share/zinit/zinit.git/zinit.zsh"
autoload -Uz _zinit
(( ${+_comps} )) && _comps[zinit]=_zinit


# Zinit Plugin ice
# zinit light zdharma-continuum/fast-syntax-highlighting
zinit wait lucid for \
 atinit"ZINIT[COMPINIT_OPTS]=-C; zicompinit; zicdreplay" \
    zsh-users/zsh-syntax-highlighting \
 blockf \
    zsh-users/zsh-completions \
 atload"!_zsh_autosuggest_start" \
    zsh-users/zsh-autosuggestions \
	zsh-users/zsh-history-substring-search
zinit wait"2" lucid for \
	OMZP::git \
	OMZP::web-search \
	OMZL::clipboard.zsh \
	OMZP::copypath \
	OMZP::copyfile


# Load powerlevel10k theme
zinit ice depth"1" # git clone depth
zinit light romkatv/powerlevel10k

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
