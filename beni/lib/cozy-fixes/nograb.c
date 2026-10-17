/* Usado so pelo wrapper ~/.local/bin/tuxmath do Cozy Kids Launcher.
 * Impede o jogo (SDL 1.2 via sdl12-compat) de prender o mouse em tela cheia,
 * para o botao X do launcher continuar clicavel. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>

int SDL_WM_GrabInput(int mode) { (void)mode; return 0; }
static void noop_grab(void *window, int grabbed) { (void)window; (void)grabbed; }

void *dlsym(void *handle, const char *name) {
    static void *(*real)(void *, const char *);
    if (!real) real = dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.34");
    if (!real) real = dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.2.5");
    if (name && (!strcmp(name, "SDL_SetWindowGrab") || !strcmp(name, "SDL_SetWindowMouseGrab")))
        return (void *)noop_grab;
    return real(handle, name);
}

/* Jogos que usam SDL2 diretamente (ex.: Pingus) */
void SDL_SetWindowGrab(void *window, int grabbed) { (void)window; (void)grabbed; }
void SDL_SetWindowMouseGrab(void *window, int grabbed) { (void)window; (void)grabbed; }
