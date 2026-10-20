/* ===================================================================
   El paso del informe operativo a una seccion (Gabriele, 20-oct-2026,
   docs/68): el cuadrado pulsado crece y se convierte en la pagina que se
   abre, sin corte entre las dos.

   Es una transicion entre documentos del navegador (View Transitions): el
   cuadrado de la pagina que se va y la pagina entera que llega llevan el
   mismo nombre, «cuadro», y el navegador lleva uno al otro: el sitio y el
   tamaño del cuadrado crecen hasta la pantalla mientras su imagen se funde
   con la de la pagina nueva.

   Solo cuando se llega pulsando un cuadrado: el informe deja una marca en
   sessionStorage y la pagina nueva la borra al leerla. Cualquier otra
   navegacion sigue como siempre. El navegador que no sabe hacerlo (Firefox,
   Safari antiguo) se queda con la animacion propia del informe.

   Va en el <head> de cada pagina, antes del primer pintado.
   =================================================================== */
(function(){
  "use strict";
  const CLAVE = "digivend.abre";
  const soporta = "onpagereveal" in window && "onpageswap" in window;
  window.digivendTransicion = {
    soporta,
    marca(){ try{ sessionStorage.setItem(CLAVE, String(Date.now())); return true; }catch(e){ return false; } },
  };
  if(!soporta) return;

  const estilo = document.createElement("style");
  estilo.textContent = `
@view-transition{navigation:auto}
::view-transition-group(cuadro){
  animation-duration:.62s;animation-timing-function:cubic-bezier(.6,0,.2,1);
  overflow:hidden;border-radius:0;
}
::view-transition-image-pair(cuadro){isolation:isolate}
::view-transition-old(cuadro),::view-transition-new(cuadro){
  width:100%;height:100%;object-fit:cover;object-position:top left;
}
::view-transition-old(cuadro){animation:dg-cuadro-sale .62s cubic-bezier(.5,0,.6,1) both}
::view-transition-new(cuadro){animation:dg-cuadro-entra .62s cubic-bezier(.4,0,.2,1) both}
::view-transition-old(root){animation:dg-cuadro-fuera .2s ease-out both}
::view-transition-new(root){animation:none}
@keyframes dg-cuadro-sale{0%,30%{opacity:1}75%,100%{opacity:0}}
@keyframes dg-cuadro-entra{0%,30%{opacity:0}80%,100%{opacity:1}}
@keyframes dg-cuadro-fuera{to{opacity:0}}
@media (prefers-reduced-motion: reduce){
  ::view-transition-group(*),::view-transition-old(*),::view-transition-new(*){animation:none!important}
}`;
  (document.head || document.documentElement).appendChild(estilo);

  const marcado = borrar => {
    let ok = false;
    // Una marca de hace mas de unos segundos es de un clic que no llego a ninguna parte.
    try{ ok = Date.now() - Number(sessionStorage.getItem(CLAVE)) < 8000; if(borrar) sessionStorage.removeItem(CLAVE); }catch(e){}
    return ok;
  };
  // La pagina que se va: si no es el clic en un cuadrado, sin transicion.
  addEventListener("pageswap", e => {
    if(e.viewTransition && !marcado(false)) e.viewTransition.skipTransition();
  });
  // La pagina que llega: toda ella es el cuadrado que crece.
  addEventListener("pagereveal", e => {
    if(!e.viewTransition) return;
    if(!marcado(true)){ e.viewTransition.skipTransition(); return; }
    const raiz = document.documentElement;
    raiz.style.viewTransitionName = "cuadro";
    e.viewTransition.finished.finally(() => { raiz.style.viewTransitionName = ""; });
  });
})();
