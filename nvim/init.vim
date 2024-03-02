syntax on
set showmatch matchtime=3
set hlsearch
set number
set hidden
set noerrorbells
set tabstop=4 softtabstop=4
set shiftwidth=4
set expandtab
set smartindent
set nu
set nowrap
set smartcase
set noswapfile
set nobackup
set undodir=~/.config/nvim/undodir
set undofile
set incsearch
set termguicolors
set scrolloff=8
set noshowmode
set completeopt=noinsert,menuone,noselect
set ignorecase
set splitright
set updatetime=50
set pastetoggle=<C-P>

tnoremap jk <C-\><C-n> 
inoremap jk <ESC>

"Unhighlight search - spacebar
nnoremap <silent> <Space> :nohlsearch<Bar>:echo<CR>

let mapleader = " "
nnoremap <leader>h :wincmd h<CR>
nnoremap <leader>j :wincmd j<CR>
nnoremap <leader>k :wincmd k<CR>
nnoremap <leader>l :wincmd l<CR>
nnoremap <leader>u :UndotreeShow<CR>

nnoremap <leader><S-h> :wincmd H<CR>
nnoremap <leader><S-j> :wincmd J<CR>
nnoremap <leader><S-k> :wincmd K<CR>
nnoremap <leader><S-l> :wincmd L<CR>

nnoremap <leader>hs :split<CR>
nnoremap <leader>s :vsplit<CR>

" term
nnoremap <leader>t :term<CR>

" tabs
nnoremap <leader>to :tabnew<CR> 
nnoremap <leader>tn :tabnext<CR> 
nnoremap <leader>tc :tabclose<CR>

" buffers
nnoremap <leader>bn :bn<CR>
nnoremap <leader>bp :bp<CR>
nnoremap <leader>bc :bd<CR>

nnoremap <leader>e :Explore<CR>

" Find files using Telescope command-line sugar.
nnoremap <leader>ff <cmd>Telescope find_files<cr>
nnoremap <leader>fg <cmd>Telescope live_grep<cr>
nnoremap <leader>fb <cmd>Telescope buffers<cr>
nnoremap <leader>fh <cmd>Telescope help_tags<cr>

" Using Lua functions
nnoremap <leader>ff <cmd>lua require('telescope.builtin').find_files()<cr>
nnoremap <leader>fg <cmd>lua require('telescope.builtin').live_grep()<cr>
nnoremap <leader>fb <cmd>lua require('telescope.builtin').buffers()<cr>
nnoremap <leader>fh <cmd>lua require('telescope.builtin').help_tags()<cr>


if !empty(glob("~/.config/nvim/plug.vim"))
    source $HOME/.config/nvim/plug.vim
endif
