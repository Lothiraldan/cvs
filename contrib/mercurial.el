;;; mercurial.el --- Emacs support for the Mercurial distributed SCM

;; Copyright (C) 2005 Bryan O'Sullivan

;; Author: Bryan O'Sullivan <bos@serpentine.com>

;; $Id$

;; mercurial.el is free software; you can redistribute it and/or
;; modify it under the terms of version 2 of the GNU General Public
;; License as published by the Free Software Foundation.

;; mercurial.el is distributed in the hope that it will be useful, but
;; WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
;; General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with mercurial.el, GNU Emacs, or XEmacs; see the file COPYING
;; (`C-h C-l').  If not, write to the Free Software Foundation, Inc.,
;; 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

;;; Commentary:

;; This mode builds upon Emacs's VC mode to provide flexible
;; integration with the Mercurial distributed SCM tool.

;; To get going as quickly as possible, load mercurial.el into Emacs and
;; type `C-c h h'; this runs hg-help-overview, which prints a helpful
;; usage overview.

;; Much of the inspiration for mercurial.el comes from Rajesh
;; Vaidheeswarran's excellent p4.el, which does an admirably thorough
;; job for the commercial Perforce SCM product.  In fact, substantial
;; chunks of code are adapted from p4.el.

;; This code has been developed under XEmacs 21.5, and may will not
;; work as well under GNU Emacs (albeit tested under 21.2).  Patches
;; to enhance the portability of this code, fix bugs, and add features
;; are most welcome.  You can clone a Mercurial repository for this
;; package from http://www.serpentine.com/hg/hg-emacs

;; Please send problem reports and suggestions to bos@serpentine.com.


;;; Code:

(require 'advice)
(require 'cl)
(require 'diff-mode)
(require 'easymenu)
(require 'vc)


;;; XEmacs has view-less, while GNU Emacs has view.  Joy.

(condition-case nil
    (require 'view-less)
  (error nil))
(condition-case nil
    (require 'view)
  (error nil))


;;; Variables accessible through the custom system.

(defgroup mercurial nil
  "Mercurial distributed SCM."
  :group 'tools)

(defcustom hg-binary
  (dolist (path '("~/bin/hg"
		  "/usr/bin/hg"
		  "/usr/local/bin/hg"))
    (when (file-executable-p path)
      (return path)))
  "The path to Mercurial's hg executable."
  :type '(file :must-match t)
  :group 'mercurial)

(defcustom hg-mode-hook nil
  "Hook run when a buffer enters hg-mode."
  :type 'sexp
  :group 'mercurial)

(defcustom hg-global-prefix "\C-ch"
  "The global prefix for Mercurial keymap bindings."
  :type 'sexp
  :group 'mercurial)

(defcustom hg-commit-allow-empty-message nil
  "Whether to allow changes to be committed with empty descriptions."
  :type 'boolean
  :group 'mercurial)

(defcustom hg-commit-allow-empty-file-list nil
  "Whether to allow changes to be committed without any modified files."
  :type 'boolean
  :group 'mercurial)

(defcustom hg-rev-completion-limit 100
  "The maximum number of revisions that hg-read-rev will offer to complete.
This affects memory usage and performance when prompting for revisions
in a repository with a lot of history."
  :type 'integer
  :group 'mercurial)

(defcustom hg-log-limit 50
  "The maximum number of revisions that hg-log will display."
  :type 'integer
  :group 'mercurial)

(defcustom hg-update-modeline t
  "Whether to update the modeline with the status of a file after every save.
Set this to nil on platforms with poor process management, such as Windows."
  :type 'boolean
  :group 'mercurial)


;;; Other variables.

(defconst hg-running-xemacs (string-match "XEmacs" emacs-version)
  "Is mercurial.el running under XEmacs?")

(defvar hg-mode nil
  "Is this file managed by Mercurial?")
(make-variable-buffer-local 'hg-mode)
(put 'hg-mode 'permanent-local t)

(defvar hg-status nil)
(make-variable-buffer-local 'hg-status)
(put 'hg-status 'permanent-local t)

(defvar hg-output-buffer-name "*Hg*"
  "The name to use for Mercurial output buffers.")

(defvar hg-file-history nil)
(defvar hg-rev-history nil)


;;; Random constants.

(defconst hg-commit-message-start
  "--- Enter your commit message.  Type `C-c C-c' to commit. ---\n")

(defconst hg-commit-message-end
  "--- Files in bold will be committed.  Click to toggle selection. ---\n")


;;; hg-mode keymap.

(defvar hg-prefix-map
  (let ((map (copy-keymap vc-prefix-map)))
    (if (functionp 'set-keymap-name)
      (set-keymap-name map 'hg-prefix-map)); XEmacs
    map)
  "This keymap overrides some default vc-mode bindings.")
(fset 'hg-prefix-map hg-prefix-map)
(define-key hg-prefix-map "=" 'hg-diff)
(define-key hg-prefix-map "c" 'hg-undo)
(define-key hg-prefix-map "g" 'hg-annotate)
(define-key hg-prefix-map "l" 'hg-log)
(define-key hg-prefix-map "n" 'hg-commit-file)
;; (define-key hg-prefix-map "r" 'hg-update)
(define-key hg-prefix-map "u" 'hg-revert-buffer)
(define-key hg-prefix-map "~" 'hg-version-other-window)

(defvar hg-mode-map (make-sparse-keymap))
(define-key hg-mode-map "\C-xv" 'hg-prefix-map)

(add-minor-mode 'hg-mode 'hg-mode hg-mode-map)


;;; Global keymap.

(global-set-key "\C-xvi" 'hg-add)

(defvar hg-global-map (make-sparse-keymap))
(fset 'hg-global-map hg-global-map)
(global-set-key hg-global-prefix 'hg-global-map)
(define-key hg-global-map "," 'hg-incoming)
(define-key hg-global-map "." 'hg-outgoing)
(define-key hg-global-map "<" 'hg-pull)
(define-key hg-global-map "=" 'hg-diff)
(define-key hg-global-map ">" 'hg-push)
(define-key hg-global-map "?" 'hg-help-overview)
(define-key hg-global-map "A" 'hg-addremove)
(define-key hg-global-map "U" 'hg-revert)
(define-key hg-global-map "a" 'hg-add)
(define-key hg-global-map "c" 'hg-commit)
(define-key hg-global-map "f" 'hg-forget)
(define-key hg-global-map "h" 'hg-help-overview)
(define-key hg-global-map "i" 'hg-init)
(define-key hg-global-map "l" 'hg-log)
(define-key hg-global-map "r" 'hg-root)
(define-key hg-global-map "s" 'hg-status)
(define-key hg-global-map "u" 'hg-update)


;;; View mode keymap.

(defvar hg-view-mode-map
  (let ((map (copy-keymap (if (boundp 'view-minor-mode-map)
			      view-minor-mode-map
			    view-mode-map))))
    (if (functionp 'set-keymap-name)
      (set-keymap-name map 'hg-view-mode-map)); XEmacs
    map))
(fset 'hg-view-mode-map hg-view-mode-map)
(define-key hg-view-mode-map
  (if hg-running-xemacs [button2] [mouse-2])
  'hg-buffer-mouse-clicked)


;;; Commit mode keymaps.

(defvar hg-commit-mode-map (make-sparse-keymap))
(define-key hg-commit-mode-map "\C-c\C-c" 'hg-commit-finish)
(define-key hg-commit-mode-map "\C-c\C-k" 'hg-commit-abort)

(defvar hg-commit-mode-file-map (make-sparse-keymap))
(define-key hg-commit-mode-file-map
  (if hg-running-xemacs [button2] [mouse-2])
  'hg-commit-mouse-clicked)
(define-key hg-commit-mode-file-map " " 'hg-commit-toggle-file)
(define-key hg-commit-mode-file-map "\r" 'hg-commit-toggle-file)
  

;;; Convenience functions.

(defsubst hg-binary ()
  (if hg-binary
      hg-binary
    (error "No `hg' executable found!")))

(defsubst hg-replace-in-string (str regexp newtext &optional literal)
  "Replace all matches in STR for REGEXP with NEWTEXT string.
Return the new string.  Optional LITERAL non-nil means do a literal
replacement.

This function bridges yet another pointless impedance gap between
XEmacs and GNU Emacs."
  (if (fboundp 'replace-in-string)
      (replace-in-string str regexp newtext literal)
    (replace-regexp-in-string regexp newtext str nil literal)))

(defsubst hg-strip (str)
  "Strip leading and trailing white space from a string."
  (hg-replace-in-string (hg-replace-in-string str "[ \t\r\n]+$" "")
			"^[ \t\r\n]+" ""))

(defsubst hg-chomp (str)
  "Strip trailing newlines from a string."
  (hg-replace-in-string str "[\r\n]+$" ""))

(defun hg-run-command (command &rest args)
  "Run the shell command COMMAND, returning (EXIT-CODE . COMMAND-OUTPUT).
The list ARGS contains a list of arguments to pass to the command."
  (let* (exit-code
	 (output
	  (with-output-to-string
	    (with-current-buffer
		standard-output
	      (setq exit-code
		    (apply 'call-process command nil t nil args))))))
    (cons exit-code output)))

(defun hg-run (command &rest args)
  "Run the Mercurial command COMMAND, returning (EXIT-CODE . COMMAND-OUTPUT)."
  (apply 'hg-run-command (hg-binary) command args))

(defun hg-run0 (command &rest args)
  "Run the Mercurial command COMMAND, returning its output.
If the command does not exit with a zero status code, raise an error."
  (let ((res (apply 'hg-run-command (hg-binary) command args)))
    (if (not (eq (car res) 0))
	(error "Mercurial command failed %s - exit code %s"
	       (cons command args)
	       (car res))
      (cdr res))))

(defun hg-buffer-commands (pnt)
  "Use the properties of a character to do something sensible."
  (interactive "d")
  (let ((rev (get-char-property pnt 'rev))
	(file (get-char-property pnt 'file))
	(date (get-char-property pnt 'date))
	(user (get-char-property pnt 'user))
	(host (get-char-property pnt 'host))
	(prev-buf (current-buffer)))
    (cond
     (file
      (find-file-other-window file))
     (rev
      (hg-diff hg-view-file-name rev rev prev-buf))
     ((message "I don't know how to do that yet")))))

(defun hg-buffer-mouse-clicked (event)
  "Translate the mouse clicks in a HG log buffer to character events.
These are then handed off to `hg-buffer-commands'.

Handle frickin' frackin' gratuitous event-related incompatibilities."
  (interactive "e")
  (if hg-running-xemacs
      (progn
	(select-window (event-window event))
	(hg-buffer-commands (event-point event)))
    (select-window (posn-window (event-end event)))
    (hg-buffer-commands (posn-point (event-start event)))))

(unless (fboundp 'view-minor-mode)
  (defun view-minor-mode (prev-buffer exit-func)
    (view-mode)))

(defsubst hg-abbrev-file-name (file)
  "Portable wrapper around abbreviate-file-name."
  (if hg-running-xemacs
      (abbreviate-file-name file t)
    (abbreviate-file-name file)))

(defun hg-read-file-name (&optional prompt default)
  "Read a file or directory name, or a pattern, to use with a command."
  (let ((path (or default (buffer-file-name))))
    (if (or (not path) current-prefix-arg)
	(expand-file-name
	 (read-file-name (format "File, directory or pattern%s: "
				 (or prompt ""))
			 (and path (file-name-directory path))
			 nil nil
			 (and path (file-name-nondirectory path))
			 'hg-file-history))
      path)))

(defun hg-read-rev (&optional prompt default)
  "Read a revision or tag, offering completions."
  (let ((rev (or default "tip")))
    (if (or (not rev) current-prefix-arg)
	(let ((revs (split-string (hg-chomp
				   (hg-run0 "-q" "log" "-r"
					    (format "-%d"
						    hg-rev-completion-limit)
					    "-r" "tip"))
				  "[\n:]")))
	  (dolist (line (split-string (hg-chomp (hg-run0 "tags")) "\n"))
	    (setq revs (cons (car (split-string line "\\s-")) revs)))
	  (completing-read (format "Revision%s (%s): "
				   (or prompt "")
				   (or default "tip"))
			   (map 'list 'cons revs revs)
			   nil
			   nil
			   nil
			   'hg-rev-history
			   (or default "tip")))
      rev)))

(defmacro hg-do-across-repo (path &rest body)
  (let ((root-name (gensym "root-"))
	(buf-name (gensym "buf-")))
    `(let ((,root-name (hg-root ,path)))
       (save-excursion
	 (dolist (,buf-name (buffer-list))
	   (set-buffer ,buf-name)
	   (when (and hg-status (equal (hg-root buffer-file-name) ,root-name))
	     ,@body))))))

(put 'hg-do-across-repo 'lisp-indent-function 1)


;;; View mode bits.

(defun hg-exit-view-mode (buf)
  "Exit from hg-view-mode.
We delete the current window if entering hg-view-mode split the
current frame."
  (when (and (eq buf (current-buffer))
	     (> (length (window-list)) 1))
    (delete-window))
  (when (buffer-live-p buf)
    (kill-buffer buf)))

(defun hg-view-mode (prev-buffer &optional file-name)
  (goto-char (point-min))
  (set-buffer-modified-p nil)
  (toggle-read-only t)
  (view-minor-mode prev-buffer 'hg-exit-view-mode)
  (use-local-map hg-view-mode-map)
  (setq truncate-lines t)
  (when file-name
    (set (make-local-variable 'hg-view-file-name)
	 (hg-abbrev-file-name file-name))))
  
(defun hg-file-status (file)
  "Return status of FILE, or nil if FILE does not exist or is unmanaged."
  (let* ((s (hg-run "status" file))
	 (exit (car s))
	 (output (cdr s)))
    (if (= exit 0)
	(let ((state (assoc (substring output 0 (min (length output) 2))
			    '(("M " . modified)
			      ("A " . added)
			      ("R " . removed)
			      ("? " . nil)))))
	  (if state
	      (cdr state)
	    'normal)))))

(defun hg-tip ()
  (split-string (hg-chomp (hg-run0 "-q" "tip")) ":"))

(defmacro hg-view-output (args &rest body)
  "Execute BODY in a clean buffer, then quickly display that buffer.
If the buffer contains one line, its contents are displayed in the
minibuffer.  Otherwise, the buffer is displayed in view-mode.
ARGS is of the form (BUFFER-NAME &optional FILE), where BUFFER-NAME is
the name of the buffer to create, and FILE is the name of the file
being viewed."
  (let ((prev-buf (gensym "prev-buf-"))
	(v-b-name (car args))
	(v-m-rest (cdr args)))
    `(let ((view-buf-name ,v-b-name)
	   (,prev-buf (current-buffer)))
       (get-buffer-create view-buf-name)
       (kill-buffer view-buf-name)
       (get-buffer-create view-buf-name)
       (set-buffer view-buf-name)
       (save-excursion
	 ,@body)
       (case (count-lines (point-min) (point-max))
	 ((0)
	  (kill-buffer view-buf-name)
	  (message "(No output)"))
	 ((1)
	  (let ((msg (hg-chomp (buffer-substring (point-min) (point-max)))))
	    (kill-buffer view-buf-name)
	    (message "%s" msg)))
	 (t
	  (pop-to-buffer view-buf-name)
	  (hg-view-mode ,prev-buf ,@v-m-rest))))))

(put 'hg-view-output 'lisp-indent-function 1)

;;; Context save and restore across revert.

(defun hg-position-context (pos)
  "Return information to help find the given position again."
  (let* ((end (min (point-max) (+ pos 98))))
    (list pos
	  (buffer-substring (max (point-min) (- pos 2)) end)
	  (- end pos))))

(defun hg-buffer-context ()
  "Return information to help restore a user's editing context.
This is useful across reverts and merges, where a context is likely
to have moved a little, but not really changed."
  (let ((point-context (hg-position-context (point)))
	(mark-context (let ((mark (mark-marker)))
			(and mark (hg-position-context mark)))))
    (list point-context mark-context)))
	
(defun hg-find-context (ctx)
  "Attempt to find a context in the given buffer.
Always returns a valid, hopefully sane, position."
  (let ((pos (nth 0 ctx))
	(str (nth 1 ctx))
	(fixup (nth 2 ctx)))
    (save-excursion
      (goto-char (max (point-min) (- pos 15000)))
      (if (and (not (equal str ""))
	       (search-forward str nil t))
	  (- (point) fixup)
	(max pos (point-min))))))

(defun hg-restore-context (ctx)
  "Attempt to restore the user's editing context."
  (let ((point-context (nth 0 ctx))
	(mark-context (nth 1 ctx)))
    (goto-char (hg-find-context point-context))
    (when mark-context
      (set-mark (hg-find-context mark-context)))))


;;; Hooks.

(defun hg-mode-line (&optional force)
  "Update the modeline with the current status of a file.
An update occurs if optional argument FORCE is non-nil,
hg-update-modeline is non-nil, or we have not yet checked the state of
the file."
  (when (and (hg-root) (or force hg-update-modeline (not hg-mode)))
    (let ((status (hg-file-status buffer-file-name)))
      (setq hg-status status
	    hg-mode (and status (concat " Hg:"
					(car (hg-tip))
					(cdr (assq status
						   '((normal . "")
						     (removed . "r")
						     (added . "a")
						     (modified . "m")))))))
      status)))

(defun hg-find-file-hook ()
  (when (hg-mode-line)
    (run-hooks 'hg-mode-hook)))

(add-hook 'find-file-hooks 'hg-find-file-hook)

(defun hg-after-save-hook ()
  (let ((old-status hg-status))
    (hg-mode-line)
    (if (and (not old-status) hg-status)
	(run-hooks 'hg-mode-hook))))

(add-hook 'after-save-hook 'hg-after-save-hook)


;;; User interface functions.

(defun hg-help-overview ()
  "This is an overview of the Mercurial SCM mode for Emacs.

You can find the source code, license (GPL v2), and credits for this
code by typing `M-x find-library mercurial RET'.

The Mercurial mode user interface is based on that of the older VC
mode, so if you're already familiar with VC, the same keybindings and
functions will generally work.

Below is a list of common SCM tasks, with the key bindings needed to
perform them, and the command names.  This list is not exhaustive.

In the list below, `G/L' indicates whether a key binding is global (G)
or local (L).  Global keybindings work on any file inside a Mercurial
repository.  Local keybindings only apply to files under the control
of Mercurial.  Many commands take a prefix argument.


SCM Task                              G/L  Key Binding  Command Name
--------                              ---  -----------  ------------
Help overview (what you are reading)  G    C-c h h      hg-help-overview

Tell Mercurial to manage a file       G    C-c h a      hg-add
Commit changes to current file only   L    C-x v n      hg-commit
Undo changes to file since commit     L    C-x v u      hg-revert-buffer

Diff file vs last checkin             L    C-x v =      hg-diff

View file change history              L    C-x v l      hg-log
View annotated file                   L    C-x v a      hg-annotate

Diff repo vs last checkin             G    C-c h =      hg-diff
View status of files in repo          G    C-c h s      hg-status
Commit all changes                    G    C-c h c      hg-commit

Undo all changes since last commit    G    C-c h U      hg-revert
View repo change history              G    C-c h l      hg-log

See changes that can be pulled        G    C-c h ,      hg-incoming
Pull changes                          G    C-c h <      hg-pull
Update working directory after pull   G    C-c h u      hg-update
See changes that can be pushed        G    C-c h .      hg-outgoing
Push changes                          G    C-c h >      hg-push"
  (interactive)
  (hg-view-output ("Mercurial Help Overview")
    (insert (documentation 'hg-help-overview))))

(defun hg-add (path)
  "Add PATH to the Mercurial repository on the next commit.
With a prefix argument, prompt for the path to add."
  (interactive (list (hg-read-file-name " to add")))
  (let ((buf (current-buffer))
	(update (equal buffer-file-name path)))
    (hg-view-output (hg-output-buffer-name)
      (apply 'call-process (hg-binary) nil t nil (list "add" path)))
    (when update
      (with-current-buffer buf
	(hg-mode-line)))))

(defun hg-addremove ()
  (interactive)
  (error "not implemented"))

(defun hg-annotate ()
  (interactive)
  (error "not implemented"))

(defun hg-commit-toggle-file (pos)
  "Toggle whether or not the file at POS will be committed."
  (interactive "d")
  (save-excursion
    (goto-char pos)
    (let ((face (get-text-property pos 'face))
	  bol)
      (beginning-of-line)
      (setq bol (+ (point) 4))
      (end-of-line)
      (if (eq face 'bold)
	  (progn
	    (remove-text-properties bol (point) '(face nil))
	    (message "%s will not be committed"
		     (buffer-substring bol (point))))
	(add-text-properties bol (point) '(face bold))
	(message "%s will be committed"
		 (buffer-substring bol (point)))))))
	
(defun hg-commit-mouse-clicked (event)
  "Toggle whether or not the file at POS will be committed."
  (interactive "@e")
  (hg-commit-toggle-file (event-point event)))

(defun hg-commit-abort ()
  (interactive)
  (let ((buf hg-prev-buffer))
    (kill-buffer nil)
    (switch-to-buffer buf)))

(defun hg-commit-finish ()
  (interactive)
  (goto-char (point-min))
  (search-forward hg-commit-message-start)
  (let ((root hg-root)
	message files)
    (let ((start (point)))
      (goto-char (point-max))
      (search-backward hg-commit-message-end)
      (setq message (hg-strip (buffer-substring start (point)))))
    (when (and (= (length message) 0)
	       (not hg-commit-allow-empty-message))
      (error "Cannot proceed - commit message is empty"))
    (forward-line 1)
    (beginning-of-line)
    (while (< (point) (point-max))
      (let ((pos (+ (point) 4)))
	(end-of-line)
	(when (eq (get-text-property pos 'face) 'bold)
	  (end-of-line)
	  (setq files (cons (buffer-substring pos (point)) files))))
      (forward-line 1))
    (when (and (= (length files) 0)
	       (not hg-commit-allow-empty-file-list))
      (error "Cannot proceed - no files to commit"))
    (setq message (concat message "\n"))
    (apply 'hg-run0 "--cwd" hg-root "commit" "-m" message files)
    (let ((buf hg-prev-buffer))
      (kill-buffer nil)
      (switch-to-buffer buf))
    (hg-do-across-repo root
      (hg-mode-line))))

(defun hg-commit-mode ()
  "Mode for describing a commit of changes to a Mercurial repository.
This involves two actions: describing the changes with a commit
message, and choosing the files to commit.

To describe the commit, simply type some text in the designated area.

By default, all modified, added and removed files are selected for
committing.  Files that will be committed are displayed in bold face\;
those that will not are displayed in normal face.

To toggle whether a file will be committed, move the cursor over a
particular file and hit space or return.  Alternatively, middle click
on the file.

When you are finished with preparations, type \\[hg-commit-finish] to
proceed with the commit."
  (interactive)
  (use-local-map hg-commit-mode-map)
  (set-syntax-table text-mode-syntax-table)
  (setq local-abbrev-table text-mode-abbrev-table
	major-mode 'hg-commit-mode
	mode-name "Hg-Commit")
  (set-buffer-modified-p nil)
  (setq buffer-undo-list nil)
  (run-hooks 'text-mode-hook 'hg-commit-mode-hook))

(defun hg-commit ()
  (interactive)
  (let ((root (hg-root))
	(prev-buffer (current-buffer)))
    (unless root
      (error "Cannot commit outside a repository!"))
    (hg-do-across-repo
	(vc-buffer-sync))
    (let* ((buf-name (format "*Mercurial: Commit %s*" root)))
      (pop-to-buffer (get-buffer-create buf-name))
      (when (= (point-min) (point-max))
	(set (make-local-variable 'hg-root) root)
	(set (make-local-variable 'hg-prev-buffer) prev-buffer)
	(insert "\n")
	(let ((bol (point)))
	  (insert hg-commit-message-end)
	  (add-text-properties bol (point) '(read-only t face bold-italic)))
	(let ((file-area (point)))
	  (insert (hg-chomp (hg-run0 "--cwd" root "status" "-arm")))
	  (goto-char file-area)
	  (while (< (point) (point-max))
	    (let ((bol (point)))
	      (forward-char 1)
	      (insert "  ")
	      (end-of-line)
	      (add-text-properties (+ bol 4) (point)
				   '(face bold mouse-face highlight)))
	    (forward-line 1))
	  (goto-char file-area)
	  (add-text-properties (point) (point-max)
			       `(read-only t keymap ,hg-commit-mode-file-map))
	  (goto-char (point-min))
	  (insert hg-commit-message-start)
	  (add-text-properties (point-min) (point)
			       '(read-only t face bold-italic))
	  (insert "\n\n")
	  (forward-line -1)
	  (hg-commit-mode))))))

(defun hg-diff (path &optional rev1 rev2)
  "Show the differences between REV1 and REV2 of PATH.
When called interactively, the default behaviour is to treat REV1 as
the tip revision, REV2 as the current edited version of the file, and
PATH as the file edited in the current buffer.
With a prefix argument, prompt for all of these."
  (interactive (list (hg-read-file-name " to diff")
		     (hg-read-rev " to start with")
		     (let ((rev2 (hg-read-rev " to end with" 'working-dir)))
		       (and (not (eq rev2 'working-dir)) rev2))))
  (unless rev1
    (setq rev1 "-1"))
  (let ((a-path (hg-abbrev-file-name path))
	diff)
    (hg-view-output ((if (equal rev1 rev2)
			 (format "Mercurial: Rev %s of %s" rev1 a-path)
		       (format "Mercurial: Rev %s to %s of %s"
			       rev1 (or rev2 "Current") a-path)))
      (if rev2
	  (call-process (hg-binary) nil t nil "diff" "-r" rev1 "-r" rev2 path)
	(call-process (hg-binary) nil t nil "diff" "-r" rev1 path))
      (diff-mode)
      (setq diff (not (= (point-min) (point-max))))
      (font-lock-fontify-buffer))
    diff))

(defun hg-forget (path)
  "Lose track of PATH, which has been added, but not yet committed.
This will prevent the file from being incorporated into the Mercurial
repository on the next commit.
With a prefix argument, prompt for the path to forget."
  (interactive (list (hg-read-file-name " to forget")))
  (let ((buf (current-buffer))
	(update (equal buffer-file-name path)))
    (hg-view-output (hg-output-buffer-name)
      (apply 'call-process (hg-binary) nil t nil (list "forget" path)))
    (when update
      (with-current-buffer buf
	(hg-mode-line)))))
  
(defun hg-incoming ()
  (interactive)
  (error "not implemented"))

(defun hg-init ()
  (interactive)
  (error "not implemented"))

(defun hg-log (path &optional rev1 rev2)
  "Display the revision history of PATH, between REV1 and REV2.
REV1 defaults to the initial revision, while REV2 defaults to the tip.
With a prefix argument, prompt for each parameter."
  (interactive (list (hg-read-file-name " to log")
		     (hg-read-rev " to start with" "-1")
		     (hg-read-rev " to end with" (format "-%d" hg-log-limit))))
  (let ((a-path (hg-abbrev-file-name path)))
    (hg-view-output ((if (equal rev1 rev2)
			 (format "Mercurial: Rev %s of %s" rev1 a-path)
		       (format "Mercurial: Rev %s to %s of %s"
			       rev1 (or rev2 "Current") a-path)))
      (call-process (hg-binary) nil t nil "log" "-r" rev1 "-r" rev2 path)
      (diff-mode)
      (font-lock-fontify-buffer))))

(defun hg-outgoing ()
  (interactive)
  (error "not implemented"))

(defun hg-pull ()
  (interactive)
  (error "not implemented"))

(defun hg-push ()
  (interactive)
  (error "not implemented"))

(defun hg-revert-buffer-internal ()
  (let ((ctx (hg-buffer-context)))
    (message "Reverting %s..." buffer-file-name)
    (hg-run0 "revert" buffer-file-name)
    (revert-buffer t t t)
    (hg-restore-context ctx)
    (hg-mode-line)
    (message "Reverting %s...done" buffer-file-name)))

(defun hg-revert-buffer ()
  "Revert current buffer's file back to the latest committed version.
If the file has not changed, nothing happens.  Otherwise, this
displays a diff and asks for confirmation before reverting."
  (interactive)
  (let ((vc-suppress-confirm nil)
	(obuf (current-buffer))
	diff)
    (vc-buffer-sync)
    (unwind-protect
	(setq diff (hg-diff buffer-file-name))
      (when diff
	(unless (yes-or-no-p "Discard changes? ")
	  (error "Revert cancelled")))
      (when diff
	(let ((buf (current-buffer)))
	  (delete-window (selected-window))
	  (kill-buffer buf))))
    (set-buffer obuf)
    (when diff
      (hg-revert-buffer-internal))))

(defun hg-root (&optional path)
  "Return the root of the repository that contains the given path.
If the path is outside a repository, return nil.
When called interactively, the root is printed.  A prefix argument
prompts for a path to check."
  (interactive (list (hg-read-file-name)))
  (let ((root (do ((prev nil dir)
		   (dir (file-name-directory (or path buffer-file-name ""))
			(file-name-directory (directory-file-name dir))))
		  ((equal prev dir))
		(when (file-directory-p (concat dir ".hg"))
		  (return dir)))))
    (when (interactive-p)
      (if root
	  (message "The root of this repository is `%s'." root)
	(message "The path `%s' is not in a Mercurial repository."
		 (abbreviate-file-name path t))))
    root))

(defun hg-status (path)
  "Print revision control status of a file or directory.
With prefix argument, prompt for the path to give status for.
Names are displayed relative to the repository root."
  (interactive (list (hg-read-file-name " for status" (hg-root))))
  (let ((root (hg-root)))
    (hg-view-output ((format "Mercurial: Status of %s in %s"
			     (let ((name (substring (expand-file-name path)
						    (length root))))
			       (if (> (length name) 0)
				   name
				 "*"))
			     (hg-abbrev-file-name root)))
      (apply 'call-process (hg-binary) nil t nil
	     (list "--cwd" root "status" path)))))

(defun hg-undo ()
  (interactive)
  (error "not implemented"))

(defun hg-version-other-window ()
  (interactive)
  (error "not implemented"))


(provide 'mercurial)


;;; Local Variables:
;;; prompt-to-byte-compile: nil
;;; end:
