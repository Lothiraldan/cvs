/*
 * Utility functions
 *
 * Copyright (c) 2011 Yuya Nishihara <yuya@tcha.org>
 *
 * This software may be used and distributed according to the terms of the
 * GNU General Public License version 2 or any later version.
 */

#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include "util.h"

void abortmsg(const char *fmt, ...)
{
	va_list args;
	va_start(args, fmt);
	fputs("\033[1;31mchg: abort: ", stderr);
	vfprintf(stderr, fmt, args);
	fputs("\033[m\n", stderr);
	va_end(args);

	exit(255);
}

static int debugmsgenabled = 0;

void enabledebugmsg(void)
{
	debugmsgenabled = 1;
}

void debugmsg(const char *fmt, ...)
{
	if (!debugmsgenabled)
		return;

	va_list args;
	va_start(args, fmt);
	fputs("\033[1;30mchg: debug: ", stderr);
	vfprintf(stderr, fmt, args);
	fputs("\033[m\n", stderr);
	va_end(args);
}

void *mallocx(size_t size)
{
	void *result = malloc(size);
	if (!result)
		abortmsg("failed to malloc");
	return result;
}

void *reallocx(void *ptr, size_t size)
{
	void *result = realloc(ptr, size);
	if (!result)
		abortmsg("failed to realloc");
	return result;
}

/*
 * Execute a shell command in mostly the same manner as system(), with the
 * give environment variables, after chdir to the given cwd. Returns a status
 * code compatible with the Python subprocess module.
 */
int runshellcmd(const char *cmd, const char *envp[], const char *cwd)
{
	enum { F_SIGINT = 1, F_SIGQUIT = 2, F_SIGMASK = 4, F_WAITPID = 8 };
	unsigned int doneflags = 0;
	int status = 0;
	struct sigaction newsa, oldsaint, oldsaquit;
	sigset_t oldmask;

	/* block or mask signals just as system() does */
	memset(&newsa, 0, sizeof(newsa));
	newsa.sa_handler = SIG_IGN;
	newsa.sa_flags = 0;
	if (sigemptyset(&newsa.sa_mask) < 0)
		goto done;
	if (sigaction(SIGINT, &newsa, &oldsaint) < 0)
		goto done;
	doneflags |= F_SIGINT;
	if (sigaction(SIGQUIT, &newsa, &oldsaquit) < 0)
		goto done;
	doneflags |= F_SIGQUIT;

	if (sigaddset(&newsa.sa_mask, SIGCHLD) < 0)
		goto done;
	if (sigprocmask(SIG_BLOCK, &newsa.sa_mask, &oldmask) < 0)
		goto done;
	doneflags |= F_SIGMASK;

	pid_t pid = fork();
	if (pid < 0)
		goto done;
	if (pid == 0) {
		sigaction(SIGINT, &oldsaint, NULL);
		sigaction(SIGQUIT, &oldsaquit, NULL);
		sigprocmask(SIG_SETMASK, &oldmask, NULL);
		if (cwd && chdir(cwd) < 0)
			_exit(127);
		const char *argv[] = {"sh", "-c", cmd, NULL};
		if (envp) {
			execve("/bin/sh", (char **)argv, (char **)envp);
		} else {
			execv("/bin/sh", (char **)argv);
		}
		_exit(127);
	} else {
		if (waitpid(pid, &status, 0) < 0)
			goto done;
		doneflags |= F_WAITPID;
	}

done:
	if (doneflags & F_SIGINT)
		sigaction(SIGINT, &oldsaint, NULL);
	if (doneflags & F_SIGQUIT)
		sigaction(SIGQUIT, &oldsaquit, NULL);
	if (doneflags & F_SIGMASK)
		sigprocmask(SIG_SETMASK, &oldmask, NULL);

	/* no way to report other errors, use 127 (= shell termination) */
	if (!(doneflags & F_WAITPID))
		return 127;
	if (WIFEXITED(status))
		return WEXITSTATUS(status);
	if (WIFSIGNALED(status))
		return -WTERMSIG(status);
	return 127;
}
