"Unhighlight search - spacebar
nnoremap <silent> <Space> :nohlsearch<Bar>:echo<CR>

let mapleader = " "
nnoremap <leader>j :call VSCodeNotify('workbench.action.navigateDown')<CR>
nnoremap <leader>k :call VSCodeNotify('workbench.action.navigateUp')<CR>
nnoremap <leader>h :call VSCodeNotify('workbench.action.navigateLeft')<CR>
nnoremap <leader>l :call VSCodeNotify('workbench.action.navigateRight')<CR>

nnoremap <leader><S-l> :call VSCodeNotify('workbench.action.moveEditorToRightGroup')<CR>
nnoremap <leader><S-h> :call VSCodeNotify('workbench.action.moveEditorToLeftGroup')<CR>
nnoremap <leader><S-j> :call VSCodeNotify('workbench.action.moveEditorToBelowGroup')<CR>
nnoremap <leader><S-k> :call VSCodeNotify('workbench.action.moveEditorToAboveGroup')<CR>

nnoremap <leader>hs :call VSCodeNotify('workbench.action.splitEditorDown')<CR>
nnoremap <leader>s :call VSCodeNotify('workbench.action.splitEditor')<CR>

" term
nnoremap <leader>t :call VSCodeNotify('workbench.action.togglePanel')<CR>

" buffers
nnoremap <leader>n :call VSCodeNotify('workbench.action.nextEditor')<CR>
nnoremap <leader><S-n> :call VSCodeNotify('workbench.action.previousEditor')<CR>

nnoremap <leader>e :call VSCodeNotify('workbench.view.explorer')<CR>
nnoremap <leader><S-e> :call VSCodeNotify('workbench.action.toggleSidebarVisibility')<CR>

nnoremap <silent> <leader> :call VSCodeNotify('whichkey.show')<CR>

" GoTo code navigation.
"nmap <leader>gd <Plug>(coc-definition)

" Use K to show documentation in preview window
"nnoremap <silent> K :call <SID>show_documentation()<CR>
