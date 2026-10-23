/* ===================================================================
   El asistente y Vendi, su muñeco (docs/40 y docs/69).

   Una sola pieza para todas las paginas que lo llevan: el panel y el informe
   general operativo. La pagina la monta con

       Asistente.monta({ pagina: "operativo", sugerencias: () => [...] })

   y esto pone el resto: el muñeco flotante, el bocadillo, el cajon del chat y
   la conversacion con /api/pregunta.

   Lo que lo hace seguro no esta aqui: el servidor le pasa al modelo los MISMOS
   datos recortados que esta pagina recibe para esa sesion, y no tiene otra via
   al dato. La pagina solo dice cual es (`pagina`); el perfil lo pone la sesion.

   - Vendi es una maquina de snacks del azul del logo de Serunion Vending
     (#0f5b84), con ojos, guantes y zapatillas, en SVG: ni imagen ni nada que
     pedir fuera del dominio (CLAUDE.md). Es el de siempre: cada usuario puede
     elegir otro (Tom, Kiko, Furgo o Bufy) y se le guarda (docs/76).
   - Saluda con la mano al entrar (despues de la bienvenida, si la hay), al
     pasarle el raton y al abrir el cajon. Con «reducir movimiento», quieto.
   - Las respuestas traen negritas, listas y tablas: se pintan escapando
     antes de dar formato. Cada tabla se baja a Excel (comun/xlsx.js, que se
     carga al pulsar) o a PDF (la ventana de imprimir, solo con la tabla).
   - Una pregunta larga va por pasos (docs/71): el servidor devuelve `sigue`
     y aqui se vuelve a llamar con ese id, ensenando que seccion esta mirando.
   - La conversacion se guarda en sessionStorage: sigue al cambiar de pagina
     en la misma pestana y se pierde al cerrarla. Al salir se borra.
   =================================================================== */
(function(){
  "use strict";

  const CSS = `
.as-fondo{position:fixed;inset:0;background:rgba(0,0,0,.28);opacity:0;pointer-events:none;transition:opacity .15s;z-index:40}
.as-fondo.vis{opacity:1;pointer-events:auto}
#chat{
  position:fixed;top:0;right:0;bottom:0;width:min(440px,100%);z-index:41;
  background:var(--tarjeta);border-left:1px solid var(--borde);display:flex;flex-direction:column;
  transform:translateX(100%);transition:transform .18s ease-out;box-shadow:-8px 0 28px rgba(0,0,0,.12)
}
#chat.vis{transform:none}
#chat header{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:14px 16px;border-bottom:1px solid var(--borde)}
#chat header #chatQuedan{order:9;flex-basis:100%;padding-left:38px;margin-top:-6px}
#chat header #chatQuedan:empty{display:none}
#chat header b{font-size:15px;flex:1}
#chat header span{font-size:12px;color:var(--tinta-3);white-space:nowrap}
#chat .hilo{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:12px}
.turno{max-width:92%;font-size:14px;line-height:1.5;overflow-wrap:anywhere}
.turno p{margin:0 0 6px}.turno p:last-child{margin:0}
.turno ul{margin:0 0 6px;padding-left:18px}
.turno .tabla{margin:6px 0 10px;border:1px solid var(--borde);border-radius:10px;overflow:hidden;background:var(--tarjeta)}
.turno .tabla .rueda{overflow-x:auto}
.turno table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
.turno th{background:color-mix(in srgb, var(--s1) 9%, var(--fondo));color:var(--tinta-2);font-weight:600;text-align:left;padding:8px 12px;white-space:nowrap}
.turno td{padding:8px 12px;border-top:1px solid var(--borde);white-space:nowrap}
.turno tbody tr:nth-child(even) td{background:color-mix(in srgb, var(--fondo) 55%, transparent)}
.turno td.n,.turno th.n{text-align:right}
.turno .bajar{display:flex;gap:6px;justify-content:flex-end;padding:6px 8px;border-top:1px solid var(--borde)}
.turno .bajar button{font:inherit;font-size:12px;color:var(--tinta-2);background:transparent;border:1px solid var(--borde-fuerte);border-radius:999px;padding:3px 10px;cursor:pointer}
.turno .bajar button:hover{color:var(--tinta);border-color:var(--tinta-3)}
.turno.espera{color:var(--tinta-3);font-style:italic}
.turno .apuntado{display:block;margin-top:6px;font-size:12px;color:var(--tinta-3)}
.turno.memoria .acciones{display:flex;gap:6px;margin-top:10px}
.turno.memoria .acciones button{font:inherit;font-size:12px;color:var(--tinta-2);background:transparent;border:1px solid var(--borde-fuerte);border-radius:999px;padding:3px 10px;cursor:pointer}
.turno.memoria .acciones button:hover{color:var(--tinta);border-color:var(--tinta-3)}
.turno.yo{align-self:flex-end;background:var(--s1);color:#fff;padding:8px 12px;border-radius:12px 12px 3px 12px;white-space:pre-wrap}
.turno.el{align-self:flex-start;color:var(--tinta)}
.turno.mal{align-self:flex-start;color:var(--critico,var(--rojo,#c62828))}
.turno.el .quien{display:block;font-size:11px;color:var(--tinta-3);text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px}
.sugerencias{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 10px}
.sugerencias button{
  font:inherit;font-size:12.5px;color:var(--tinta-2);background:var(--fondo);text-align:left;
  border:1px solid var(--borde);border-radius:999px;padding:5px 11px;cursor:pointer
}
.sugerencias button:hover{border-color:var(--tinta-3);color:var(--tinta)}
#chat form{display:flex;gap:8px;padding:12px 16px;border-top:1px solid var(--borde);align-items:flex-end}
#chat textarea{
  flex:1;font:inherit;font-size:14px;color:var(--tinta);background:var(--fondo);resize:none;
  border:1px solid var(--borde-fuerte);border-radius:9px;padding:8px 10px;min-height:38px;max-height:140px
}
#chat textarea:focus{outline:2px solid var(--s1);outline-offset:1px;border-color:var(--s1)}
#chat form button{
  font:inherit;font-weight:600;font-size:13px;color:#fff;background:var(--s1);
  border:1px solid var(--s1);border-radius:9px;padding:9px 14px;cursor:pointer
}
#chat form button[disabled]{opacity:.55;cursor:progress}
#chat .pieChat{padding:0 16px 12px;font-size:11.5px;color:var(--tinta-3)}
@media (max-width:520px){ #chat{width:100%} }
.muneco{display:block;overflow:visible}
.muneco .mano{transform-origin:var(--mano,92px 70px);transform-box:view-box}
.muneco .todo{transform-origin:60px 140px;transform-box:view-box}
.saluda .mano{animation:as-saluda .42s ease-in-out 6 alternate}
.saluda .todo{animation:as-bote .84s ease-in-out 3}
@keyframes as-saluda{from{transform:rotate(-16deg)}to{transform:rotate(22deg)}}
@keyframes as-bote{0%,100%{transform:none}50%{transform:translateY(-3px) rotate(-2deg)}}
.furgo .rueda{transform-box:fill-box;transform-origin:center}
.furgo.saluda .rueda{animation:as-rueda .7s linear 3}
.furgo.saluda .todo{animation:as-traqueteo .35s ease-in-out 6}
@keyframes as-rueda{to{transform:rotate(360deg)}}
@keyframes as-traqueteo{0%,100%{transform:none}50%{transform:translateY(-1.2px)}}
.bufy .cuerpo,.bufy .pata1,.bufy .pata2{transform-box:view-box}
.bufy .cuerpo{transform-origin:36px 156px}
.bufy .pata1{transform-origin:153px 162px}
.bufy .pata2{transform-origin:191px 141px}
.bufy.saluda .cuerpo{animation:as-encabrita 2.4s ease-in-out}
.bufy.saluda .pata1{animation:as-patea1 2.4s ease-in-out}
.bufy.saluda .pata2{animation:as-patea2 2.4s ease-in-out}
@keyframes as-encabrita{0%,100%{transform:none}18%,82%{transform:rotate(-30deg)}}
@keyframes as-patea1{0%,100%{transform:none}18%{transform:rotate(-60deg)}32%,60%{transform:rotate(-90deg)}46%,74%{transform:rotate(-40deg)}}
@keyframes as-patea2{0%,100%{transform:none}18%{transform:rotate(-30deg)}32%,60%{transform:rotate(0deg)}46%,74%{transform:rotate(-50deg)}}
.turno.munecos .lista{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:8px;margin-top:8px}
.turno.munecos .lista button{
  font:inherit;font-size:12px;color:var(--tinta-2);background:var(--fondo);text-align:center;cursor:pointer;
  border:1px solid var(--borde);border-radius:12px;padding:8px 6px;display:flex;flex-direction:column;align-items:center;gap:4px
}
.turno.munecos .lista button:hover{border-color:var(--tinta-3);color:var(--tinta)}
.turno.munecos .lista button[aria-pressed="true"]{border-color:var(--s1);box-shadow:0 0 0 1px var(--s1)}
.turno.munecos .lista b{color:var(--tinta);font-size:13px}
.turno.munecos .lista .muneco{width:52px;height:64px}
.turno.munecos .lista .muneco.ancho{width:100px}
#bVendi{
  position:fixed;right:18px;bottom:18px;z-index:30;width:76px;height:94px;padding:0;
  background:transparent;border:0;cursor:pointer;filter:drop-shadow(0 4px 8px rgba(0,0,0,.18))
}
#bVendi .muneco{width:100%;height:100%}
#bVendi:focus-visible{outline:2px solid var(--s1);outline-offset:4px;border-radius:12px}
#bocadillo{
  position:fixed;right:100px;bottom:70px;z-index:30;max-width:200px;
  background:var(--tarjeta);color:var(--tinta);border:1px solid var(--borde-fuerte);
  border-radius:12px 12px 3px 12px;padding:8px 12px;font-size:13px;line-height:1.4;
  box-shadow:var(--sombra);opacity:0;transform:translateY(6px);transition:opacity .25s,transform .25s;pointer-events:none
}
#bocadillo.vis{opacity:1;transform:none}
#chat header .muneco{width:30px;height:37px;flex:none}
#chat header .muneco.ancho{width:56px}
#bVendi:has(.ancho){width:128px}
#bVendi:has(.ancho) + #bocadillo{right:152px}
.btn .muneco.ancho{width:34px}
.btn .muneco{display:inline-block;width:15px;height:19px;vertical-align:-4px;margin-right:5px}
@media (max-width:520px){ #bVendi{width:60px;height:74px;right:12px;bottom:12px} #bVendi:has(.ancho){width:100px} #bVendi:has(.ancho) + #bocadillo{right:118px} #bocadillo{right:80px;bottom:52px} }
@media (prefers-reduced-motion:reduce){ .saluda .mano,.saluda .todo,.bufy.saluda *,.furgo.saluda *{animation:none} #bocadillo{transition:none} }
`;

  /* Los munecos (docs/76). Vendi es el de siempre; cada usuario puede
     elegir otro y se le guarda. Todos en SVG, aqui dentro: nada que pedir
     fuera del dominio. Los de 120x150 llevan su brazo en .mano, con el punto
     de giro en --mano; Bufy, que es la silueta de un logo, se encabrita. */
  const t = "#0b2f45";
  const doble = (d, color, w = 5) =>
    `<path d="${d}" fill="none" stroke="${t}" stroke-width="${w + 2.6}" stroke-linecap="round"/>` +
    `<path d="${d}" fill="none" stroke="${color}" stroke-width="${w}" stroke-linecap="round"/>`;
  const guante = (x, y) => `<path d="M${x-7} ${y+9}c-1-5 1-9 4-9 1-4 4-5 6-3 2-2 5-1 6 2 3 0 4 3 3 6l-2 9c-1 4-5 6-9 6s-8-3-8-7z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>`;
  const ojos = (x1, x2, y) => `
  <ellipse cx="${x1}" cy="${y}" rx="8.5" ry="10.5" fill="#fff" stroke="${t}" stroke-width="2"/>
  <ellipse cx="${x2}" cy="${y}" rx="8.5" ry="10.5" fill="#fff" stroke="${t}" stroke-width="2"/>
  <circle cx="${x1+2}" cy="${y+2}" r="4.2" fill="${t}"/><circle cx="${x2-2}" cy="${y+2}" r="4.2" fill="${t}"/>
  <circle cx="${x1+3.5}" cy="${y+0.4}" r="1.3" fill="#fff"/><circle cx="${x2-0.5}" cy="${y+0.4}" r="1.3" fill="#fff"/>`;
  const svg = (dentro, origen) => `<svg class="muneco" viewBox="0 0 120 150" aria-hidden="true" focusable="false" style="--mano:${origen}"><g class="todo">${dentro}</g></svg>`;
  let bufys = 0, furgos = 0;

  function vendi(){
    const snack=(x,y,c)=>`<rect x="${x}" y="${y}" width="9" height="10" rx="2" fill="${c}"/>`;
    return svg(`
  <path d="M48 118v15M72 118v15" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
  <path d="M36 140c0-6 6-8 12-8s9 3 9 8z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M63 140c0-5 3-8 9-8s12 2 12 8z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M29 70Q15 80 18 95" fill="none" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
  <circle cx="18" cy="99" r="7.5" fill="#fff" stroke="${t}" stroke-width="2.5"/>
  <rect x="28" y="14" width="64" height="106" rx="12" fill="#0f5b84" stroke="${t}" stroke-width="3"/>
  <rect x="33" y="19" width="54" height="5" rx="2.5" fill="#fff" opacity=".28"/>
  <ellipse cx="48" cy="34" rx="8.5" ry="10.5" fill="#fff" stroke="${t}" stroke-width="2"/>
  <ellipse cx="72" cy="34" rx="8.5" ry="10.5" fill="#fff" stroke="${t}" stroke-width="2"/>
  <circle cx="50" cy="36" r="4.2" fill="${t}"/><circle cx="70" cy="36" r="4.2" fill="${t}"/>
  <circle cx="51.5" cy="34.4" r="1.3" fill="#fff"/><circle cx="71.5" cy="34.4" r="1.3" fill="#fff"/>
  <path d="M50 46Q60 53 70 46" fill="none" stroke="${t}" stroke-width="3" stroke-linecap="round"/>
  <rect x="35" y="55" width="38" height="43" rx="4" fill="#d6ecf8" stroke="${t}" stroke-width="2"/>
  ${snack(38,58,"#f2b632")}${snack(49.5,58,"#2a78d6")}${snack(61,58,"#1baf7a")}
  ${snack(38,72,"#eb6834")}${snack(49.5,72,"#8e5bd0")}${snack(61,72,"#f2b632")}
  ${snack(38,85,"#1baf7a")}${snack(49.5,85,"#eb6834")}${snack(61,85,"#2a78d6")}
  <path d="M37 69.5h34M37 83h34" stroke="${t}" stroke-width="1.4" opacity=".55"/>
  <rect x="77" y="55" width="10" height="19" rx="2" fill="#2b2b2b"/>
  <path d="M80 59h1M84 59h1M80 63h1M84 63h1M80 67h1M84 67h1M80 71h1M84 71h1" stroke="#9fd3ff" stroke-width="2" stroke-linecap="round"/>
  <rect x="79" y="79" width="6" height="10" rx="1.5" fill="#f2c94c" stroke="${t}" stroke-width="1.4"/>
  <rect x="37" y="104" width="46" height="9" rx="3" fill="#2b2b2b"/>
  <g class="mano">
    <path d="M91 70Q106 64 106 47" fill="none" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
    <path d="M99 44c-1-5 1-9 4-9 1-4 4-5 6-3 2-2 5-1 6 2 3 0 4 3 3 6l-2 9c-1 4-5 6-9 6s-8-3-8-7z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>
  </g>`, "92px 70px");
  }

  function tom(){
    const piel = "#f8c96e", pelo = "#0d0d0d", marco = "#5a3a22", vaq = "#8fa3c2", gris = "#b9c0c8";
    const manga = (d) => `<path d="${d}" fill="#fff" stroke="${t}" stroke-width="2" stroke-linejoin="round"/>`;
    return svg(`
    <path d="M52 106v29M68 106v29" stroke="${t}" stroke-width="12.5" stroke-linecap="round"/>
    <path d="M52 106v29M68 106v29" stroke="${vaq}" stroke-width="9.5" stroke-linecap="round"/>
    <path d="M46 104h28v8H46z" fill="${vaq}"/>
    <path d="M60 106v10" stroke="#6f84a6" stroke-width="1.2" stroke-linecap="round"/>
    <path d="M40 142c0-5 4-8 11-8s9 3 9 7v2H40z" fill="#fff" stroke="${t}" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M60 143v-2c0-4 2-7 9-7s11 3 11 8z" fill="#fff" stroke="${t}" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M41 141h18M61 141h18" stroke="${gris}" stroke-width="1.6"/>
    ${manga("M40 73q-7 3-7 13l8 1z")}
    ${doble("M36 85Q32 96 36 105", piel, 5)}
    <circle cx="36.5" cy="107" r="4.2" fill="${piel}" stroke="${t}" stroke-width="2"/>
    <path d="M39 73q1-8 11-10l10-1 10 1q10 2 11 10l-2 33q-9 2-19 2t-19-2z" fill="#fff" stroke="${t}" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M60 71v13" stroke="${gris}" stroke-width="1.6"/><path d="M58 74h4M58 79h4" stroke="${gris}" stroke-width="1"/>
    <path d="M53 63l7 8 7-8" fill="#fff" stroke="${t}" stroke-width="1.8" stroke-linejoin="round"/>
    <path d="M52 63l-4 7h9zM68 63l4 7h-9z" fill="#fff" stroke="${gris}" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M64 84h8" stroke="#8b939c" stroke-width="1.6" stroke-linecap="round"/>
    <circle cx="74.5" cy="83.6" r="1.8" fill="none" stroke="#e04a4a" stroke-width="1.1"/>
    <rect x="55.5" y="57" width="9" height="8" fill="${piel}"/>
    <path d="M55.5 57v6M64.5 57v6" stroke="${t}" stroke-width="1.8"/>
    <ellipse cx="42.5" cy="41" rx="3.2" ry="5" fill="${piel}" stroke="${t}" stroke-width="1.8"/>
    <ellipse cx="77.5" cy="41" rx="3.2" ry="5" fill="${piel}" stroke="${t}" stroke-width="1.8"/>
    <path d="M44 27q-1 23 6 31 5 5 10 5t10-5q7-8 6-31z" fill="${piel}" stroke="${t}" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M42 39q-3-14 1-21 3-5 8-6l2-9 5 6 6-8 2 8q8 2 11 8 4 8 1 22l-2-9q-1-4-7-5-9-2-18 0-6 1-7 5z" fill="${pelo}" stroke="${t}" stroke-width="1.3" stroke-linejoin="round"/>
    <path d="M48 34q3-1.4 6 0M66 34q3-1.4 6 0" stroke="#5a3a22" stroke-width="1.7" stroke-linecap="round" fill="none"/>
    <rect x="45" y="36.5" width="12.5" height="9.5" rx="4" fill="#fff" fill-opacity=".25" stroke="${marco}" stroke-width="1.3"/>
    <rect x="62.5" y="36.5" width="12.5" height="9.5" rx="4" fill="#fff" fill-opacity=".25" stroke="${marco}" stroke-width="1.3"/>
    <path d="M57.5 40q2.5-1.4 5 0M45 39l-2.6-.5M75 39l2.6-.5" stroke="${marco}" stroke-width="1.2" fill="none"/>
    <ellipse cx="51.2" cy="41.4" rx="1.4" ry="2.1" fill="#3b2414"/><ellipse cx="68.8" cy="41.4" rx="1.4" ry="2.1" fill="#3b2414"/>
    <path d="M58.2 49.5q1.8 1.3 3.6 0" stroke="#b07a3c" stroke-width="1.3" fill="none" stroke-linecap="round"/>
    <path d="M54 54.5q6 2.6 12-1.2" stroke="#7a4a22" stroke-width="1.5" fill="none" stroke-linecap="round"/>
    <path d="M65.6 53.1l1.4 1.6" stroke="#7a4a22" stroke-width="1.1" stroke-linecap="round"/>
    <g class="mano">
      ${doble("M84 79Q98 75 100 57", piel, 5)}
      <path d="M95 56c-1-5 1-8 3-8 0-4 3-5 5-3 2-2 4-1 5 1 3 0 4 3 3 5l-2 8c-1 4-4 5-8 5s-7-3-6-8z" fill="${piel}" stroke="${t}" stroke-width="2" stroke-linejoin="round"/>
    </g>
    ${manga("M80 73q7 1 8 10l-8 2z")}`, "84px 78px");
  }

  function kiko(){
    const cafe = "#6b3f26", surco = "#3d2314";
    return svg(`
    <path d="M48 112v20M72 112v20" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
    <path d="M36 140c0-6 6-8 12-8s9 3 9 8z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>
    <path d="M63 140c0-5 3-8 9-8s12 2 12 8z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>
    <path d="M28 72Q14 82 17 97" fill="none" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
    <circle cx="17" cy="101" r="7.5" fill="#fff" stroke="${t}" stroke-width="2.5"/>
    <ellipse cx="60" cy="66" rx="34" ry="50" fill="${cafe}" stroke="${t}" stroke-width="3"/>
    <path d="M46 26q-12 12-12 34" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".22"/>
    <path d="M60 17q-9 7-6 16M57 88q-8 14 3 28" fill="none" stroke="${surco}" stroke-width="4.5" stroke-linecap="round"/>
    <path d="M60 17q-9 7-6 16M57 88q-8 14 3 28" fill="none" stroke="#8a5534" stroke-width="1.5" stroke-linecap="round" transform="translate(2 0)"/>
    ${ojos(47, 73, 50)}
    <path d="M48 67Q60 79 72 67" fill="#2b2b2b" stroke="${t}" stroke-width="2.6" stroke-linejoin="round"/>
    <path d="M54 72q6 4 12 0" fill="none" stroke="#eb6834" stroke-width="2.4" stroke-linecap="round"/>
    <ellipse cx="38" cy="66" rx="4.5" ry="3" fill="#eb6834" opacity=".35"/>
    <ellipse cx="82" cy="66" rx="4.5" ry="3" fill="#eb6834" opacity=".35"/>
    <g class="mano">
      <path d="M92 70Q106 64 106 47" fill="none" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
      ${guante(106, 35)}
    </g>`, "92px 70px");
  }

  function furgo(){
    /* La furgoneta de Serunion Vending de lado, como las de la calle: blanca,
       con el bisonte del logo en la parte de atras y la marca en la puerta.
       No tiene manos ni piernas: al saludar le giran las ruedas. */
    const n = ++furgos, az = "#1b6fc9", negro = "#26292c", B = "M156 204.5 145 204.5 142.7 203 142.2 201 142.7 197 151.4 161 151.2 159 148.7 156 145 154.8 139 154.4 101 148.7 96 148.3 88 146.8 68 144.3 63 144.9 59 146.5 37 159.7 34 162.1 31.9 166 31.7 170 40.4 198 40.6 202 40.4 203 39 204.2 37 204.6 26 204.5 25 204.3 23.5 203 22.7 202 22.4 200 22 193 20.7 183 19.3 165 19.5 159 20.7 154 34.1 116 36.1 109 35.4 107 33.8 105 21 98.2 14 93.2 8.7 87 6.6 83 4.7 78 3.3 69 4.7 48 5.5 46 7 45.2 9 45.5 16.2 55 16.4 59 14.6 63 12.6 71 13.5 77 14.6 80 17 83.7 24 90.1 30 92.4 39 92.4 46 89.5 52 84.8 58 84.5 68 91.4 79 96.4 87 98.4 98 98.7 104 98.2 112 96.2 122 91.3 132 83.4 139.3 74 142.4 68 144.3 63 146.1 56 146.7 49 146.2 38 144.3 31 139.6 20 139.7 16 141 13.2 143 11.5 150 8.6 158 6.7 164 5.9 178 5.7 187 6.7 195 8.7 205 12.5 209 14.6 217 19.8 227 28.2 230 29.4 234 30 241 28.9 246 29 256 30.7 265 34.6 274.1 42 281.2 52 284.2 60 285.3 68 285.1 76 284.2 82 282.1 88 263 123.9 261 126 257 128.3 237 135.5 235 135.7 231 135.4 228 134.1 217 124.9 213 122.9 210 122.8 206.1 125 178.3 154 174.2 159 162.5 171 159.4 175 158.5 179 158.5 202 156 204.5ZM231.2 83 234 81 235.1 79 235.5 77 235.2 75 233 71.7 227 68.1 222.8 64 218.8 57 217.3 50 216 49.3 214.7 51 213.7 61 214.6 68 216.6 73 219.7 78 225 82.3 228 83.5 231.2 83ZM103 91.2 97 92 88 91.5 79 89.2 71 85.2 67 82.4 63 78.7 56.6 71 52.7 63 50.7 56 50.2 43 50.6 38 52.7 31 58.7 20 64.2 14 71 8.8 79 4.8 86 2.7 93 2 104 2.8 111 4.9 119 8.9 124 12.6 130.3 19 134.3 25 138.4 35 140 47 139.4 54 138.4 59 134.4 69 128 77.6 120 84.4 113 88.3 107 90.4 103 91.2ZM71.2 68 119 27.2 120.4 24 119.6 22 118 20 112 15.8 105 12.9 97 11.4 93 11.4 86 12.6 80 14.7 74.3 18 69 22.6 66 26.2 61.6 34 59.5 42 59.4 49 60.7 57 64.9 66 66 67.3 68 68.5 71.2 68ZM96 204.5 86 204.6 84 204.5 82 203.4 79.7 201 71.8 188 60.6 169 60 167 59.9 164 60.5 161 63.7 154 65 152.9 68 152.7 82 154.8 84.4 156 84.7 158 84 159.7 75 165.1 73.7 167 73.5 170 76.9 175 98.3 199 98.3 202 96 204.5ZM189 178.2 186 177.2 184.7 175 184.7 173 186.3 169 186.7 166 188 164.5 191 162.6 205 156.1 210.4 153 210.2 151 209 150.5 200 150.1 198.5 149 198.3 147 199.2 145 209 134.7 212 134.3 214 134.7 224 142.7 227.3 146 228.2 149 227.5 152 226 154 223 156.2 193 176.3 189 178.2Z";
    const CARRO = "M15 15Q10 15 10 21V79Q10 85 16 85H187Q193 85 193 79V63Q193 55 185 52L161 44Q153 41 147 34L135 19Q131 15 125 15Z";
    const rueda = (x) => `<g class="rueda"><circle cx="${x}" cy="84" r="13" fill="${negro}"/><circle cx="${x}" cy="84" r="8.6" fill="#d9dee3" stroke="#9aa3ab" stroke-width=".8"/>` +
      [0,45,90,135,180,225,270,315].map(a => `<circle cx="${(x + 6 * Math.cos(a * Math.PI / 180)).toFixed(2)}" cy="${(84 + 6 * Math.sin(a * Math.PI / 180)).toFixed(2)}" r="1.1" fill="#7d868e"/>`).join("") +
      `<circle cx="${x}" cy="84" r="2.6" fill="#59626a"/><path d="M${x} 81.6v4.8" stroke="#c3c9ce" stroke-width=".9"/></g>`;
    return `<svg class="muneco ancho furgo" viewBox="0 0 200 100" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">
  <defs><clipPath id="fC${n}"><path d="${CARRO}"/></clipPath></defs>
  <g class="todo">
    <path d="${CARRO}" fill="#fff" stroke="#8d969e" stroke-width="1.2" stroke-linejoin="round"/>
    <g clip-path="url(#fC${n})">
      <path d="${B}" transform="translate(3.5 15) scale(.31)" fill="${az}" fill-rule="evenodd"/>
    </g>
    <path d="M106 20H131L146 40Q146 42 143 42H106Z" fill="#33414c"/>
    <path d="M110 23H128L120 39H110Z" fill="#fff" opacity=".16"/>
    <path d="M145 37q5 0 5 5v4h-6z" fill="${negro}"/>
    <path d="M62 16V84M104 16V84" stroke="#b9c0c6" stroke-width=".8"/>
    <rect x="80" y="45" width="12" height="2.6" rx="1.3" fill="${negro}"/><rect x="108" y="45" width="12" height="2.6" rx="1.3" fill="${negro}"/>
    <rect x="64" y="68" width="78" height="5" rx="2.5" fill="${negro}"/>
    <path d="M10 76H22V85H16Q10 85 10 79Z M186 72H193V79Q193 85 187 85H178Z" fill="${negro}"/>
    <path d="M184 50l7 3v4l-7-1z" fill="#cfd8df" stroke="#8d969e" stroke-width=".6"/>
    <path d="M10 46h2v14h-2z" fill="#c0392b"/>
    <path d="M27 84a15 15 0 0 1 30 0M145 84a15 15 0 0 1 30 0" fill="${negro}"/>
    <path d="${B}" transform="translate(110.5 52) scale(.028)" fill="${az}" fill-rule="evenodd"/>
    <text x="120" y="58.6" font-family="system-ui,sans-serif" font-size="6.4" font-weight="800" fill="${az}">SERUNION</text>
    <text x="140" y="63.4" text-anchor="middle" font-family="system-ui,sans-serif" font-size="2.9" font-weight="700" fill="${az}">VENDING</text>
    ${rueda(42)}${rueda(160)}
  </g></svg>`;
  }

  function bufy(){
    /* La silueta del logo de Derichebourg, tal cual, en su azul. Al saludar se
       levanta de manos como un caballo: el cuerpo gira sobre la cadera, las
       traseras se quedan en el suelo y las delanteras patean. Va en tres trozos
       del mismo trazo, recortados; los recortes se pisan un poco para que no
       se vea la costura. Lo blanco del anillo y del ojo va pintado, no hueco,
       para que en oscuro siga siendo el logo. */
    const n = ++bufys, az = "#015a82", C = "M156 204.5 145 204.5 142.7 203 142.2 201 142.7 197 151.4 161 151.2 159 148.7 156 145 154.8 139 154.4 101 148.7 96 148.3 88 146.8 68 144.3 63 144.9 59 146.5 37 159.7 34 162.1 31.9 166 31.7 170 40.4 198 40.6 202 40.4 203 39 204.2 37 204.6 26 204.5 25 204.3 23.5 203 22.7 202 22.4 200 22 193 20.7 183 19.3 165 19.5 159 20.7 154 34.1 116 36.1 109 35.4 107 33.8 105 21 98.2 14 93.2 8.7 87 6.6 83 4.7 78 3.3 69 4.7 48 5.5 46 7 45.2 9 45.5 16.2 55 16.4 59 14.6 63 12.6 71 13.5 77 14.6 80 17 83.7 24 90.1 30 92.4 39 92.4 46 89.5 52 84.8 58 84.5 68 91.4 79 96.4 87 98.4 98 98.7 104 98.2 112 96.2 122 91.3 132 83.4 139.3 74 142.4 68 144.3 63 146.1 56 146.7 49 146.2 38 144.3 31 139.6 20 139.7 16 141 13.2 143 11.5 150 8.6 158 6.7 164 5.9 178 5.7 187 6.7 195 8.7 205 12.5 209 14.6 217 19.8 227 28.2 230 29.4 234 30 241 28.9 246 29 256 30.7 265 34.6 274.1 42 281.2 52 284.2 60 285.3 68 285.1 76 284.2 82 282.1 88 263 123.9 261 126 257 128.3 237 135.5 235 135.7 231 135.4 228 134.1 217 124.9 213 122.9 210 122.8 206.1 125 178.3 154 174.2 159 162.5 171 159.4 175 158.5 179 158.5 202 156 204.5ZM231.2 83 234 81 235.1 79 235.5 77 235.2 75 233 71.7 227 68.1 222.8 64 218.8 57 217.3 50 216 49.3 214.7 51 213.7 61 214.6 68 216.6 73 219.7 78 225 82.3 228 83.5 231.2 83Z";
    return `<svg class="muneco ancho bufy" viewBox="0 0 292 210" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">
  <defs>
    <clipPath id="bR${n}"><path clip-rule="evenodd" d="M-90-90H390V300H-90ZM8 154H54V215H8ZM134 165H176V215H134Z"/></clipPath>
    <clipPath id="bT${n}"><path d="M8 148H54V215H8Z"/></clipPath>
    <clipPath id="bD${n}"><path d="M134 159H176V215H134Z"/></clipPath>
  </defs>
  <g fill="${az}" fill-rule="evenodd">
    <path clip-path="url(#bT${n})" d="${C}"/><path d="M96 204.5 86 204.6 84 204.5 82 203.4 79.7 201 71.8 188 60.6 169 60 167 59.9 164 60.5 161 63.7 154 65 152.9 68 152.7 82 154.8 84.4 156 84.7 158 84 159.7 75 165.1 73.7 167 73.5 170 76.9 175 98.3 199 98.3 202 96 204.5Z"/>
    <g class="cuerpo">
      <circle cx="95" cy="47" r="44.5" fill="#fff"/><ellipse cx="224.6" cy="66.4" rx="10.5" ry="17" fill="#fff"/>
    <circle cx="33" cy="157" r="8"/>
      <path clip-path="url(#bR${n})" d="${C}"/>
      <path d="M103 91.2 97 92 88 91.5 79 89.2 71 85.2 67 82.4 63 78.7 56.6 71 52.7 63 50.7 56 50.2 43 50.6 38 52.7 31 58.7 20 64.2 14 71 8.8 79 4.8 86 2.7 93 2 104 2.8 111 4.9 119 8.9 124 12.6 130.3 19 134.3 25 138.4 35 140 47 139.4 54 138.4 59 134.4 69 128 77.6 120 84.4 113 88.3 107 90.4 103 91.2ZM71.2 68 119 27.2 120.4 24 119.6 22 118 20 112 15.8 105 12.9 97 11.4 93 11.4 86 12.6 80 14.7 74.3 18 69 22.6 66 26.2 61.6 34 59.5 42 59.4 49 60.7 57 64.9 66 66 67.3 68 68.5 71.2 68Z"/>
      <g class="pata1"><path clip-path="url(#bD${n})" d="${C}"/></g>
      <g class="pata2"><path d="M189 178.2 186 177.2 184.7 175 184.7 173 186.3 169 186.7 166 188 164.5 191 162.6 205 156.1 210.4 153 210.2 151 209 150.5 200 150.1 198.5 149 198.3 147 199.2 145 209 134.7 212 134.3 214 134.7 224 142.7 227.3 146 228.2 149 227.5 152 226 154 223 156.2 193 176.3 189 178.2Z"/></g>
    </g>
  </g></svg>`;
  }

  const MUNECOS = {
    vendi: ["Vendi", "la máquina de snacks", vendi],
    tom: ["Tom", "el compañero de polo blanco", tom],
    kiko: ["Kiko", "el grano de café", kiko],
    furgo: ["Furgo", "la furgoneta de Serunion Vending", furgo],
    bufy: ["Bufy", "el bisonte de Derichebourg", bufy],
  };

  function saluda(sitio){
    const m = sitio && sitio.querySelector(".muneco");
    if(!m) return;
    m.classList.remove("saluda"); void m.getBoundingClientRect(); m.classList.add("saluda");
  }

  const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  /* Negritas, sobre el texto ya escapado: lo unico que se deja pasar es <b>. */
  const linea = s => esc(s).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  const esNumero = s => /^[\s−\-+]*[\d.,]+\s*(%|€|h|min|km|uds?\.?)?\s*$/.test(s.replace(/<\/?b>/g, ""));

  /* La respuesta, en parrafos, listas y tablas. Todo lo que llega del modelo
     se escapa antes de darle formato. */
  function formatea(texto){
    const lineas = String(texto).split("\n"), out = [];
    for(let i = 0; i < lineas.length; ){
      const l = lineas[i].trim();
      if(!l){ i++; continue; }
      if(l.startsWith("|")){
        const filas = [];
        while(i < lineas.length && lineas[i].trim().startsWith("|")) filas.push(lineas[i++].trim());
        const celdas = f => f.replace(/^\||\|$/g, "").split("|").map(c => linea(c.trim()));
        const cuerpo = filas.filter(f => !/^\|[\s:|-]+\|?$/.test(f)).map(celdas);
        if(!cuerpo.length) continue;
        const [cab, ...resto] = cuerpo;
        const num = cab.map((_, j) => resto.length > 0 && resto.every(f => !f[j] || esNumero(f[j])));
        out.push('<div class="tabla"><div class="rueda"><table><thead><tr>' +
          cab.map((c, j) => `<th${num[j] ? ' class="n"' : ""}>${c}</th>`).join("") + "</tr></thead><tbody>" +
          resto.map(f => "<tr>" + f.map((c, j) => `<td${num[j] ? ' class="n"' : ""}>${c}</td>`).join("") + "</tr>").join("") +
          '</tbody></table></div><div class="bajar"><button type="button" data-bajar="xlsx">Excel</button>' +
          '<button type="button" data-bajar="pdf">PDF</button></div></div>');
        continue;
      }
      if(/^[-*•]\s+/.test(l)){
        const items = [];
        while(i < lineas.length && /^[-*•]\s+/.test(lineas[i].trim())) items.push(linea(lineas[i++].trim().replace(/^[-*•]\s+/, "")));
        out.push("<ul>" + items.map(x => `<li>${x}</li>`).join("") + "</ul>");
        continue;
      }
      out.push(`<p>${linea(l.replace(/^#+\s*/, ""))}</p>`);
      i++;
    }
    return out.join("");
  }

  /* ---------------------------------------------------- bajar una tabla */
  const sinFormato = s => s.replace(/\s+/g, " ").trim();
  /* «1.234,56 €» -> 1234.56; lo que no es una cifra se queda como texto. */
  function cifra(s){
    const t = sinFormato(s).replace(/[€%]|\b(h|min|km|uds?\.?)\b/g, "").replace(/\s/g, "").replace("−", "-");
    if(!/^[-+]?[\d.]*\d(,\d+)?$/.test(t)) return null;
    const n = Number(t.replace(/\./g, "").replace(",", "."));
    return isFinite(n) ? n : null;
  }
  function deTabla(tabla){
    const cab = [...tabla.querySelectorAll("thead th")].map(th => sinFormato(th.textContent));
    const filas = [...tabla.querySelectorAll("tbody tr")].map(tr => [...tr.children].map(td => sinFormato(td.textContent)));
    return {cab, filas};
  }
  function nombreFichero(ext){
    const d = new Date(), dos = n => String(n).padStart(2, "0");
    return `vendi_${d.getFullYear()}-${dos(d.getMonth()+1)}-${dos(d.getDate())}_${dos(d.getHours())}${dos(d.getMinutes())}.${ext}`;
  }
  let cargandoXlsx = null;
  function xlsxListo(){
    if(window.XLSX) return Promise.resolve();
    if(!cargandoXlsx) cargandoXlsx = new Promise((ok, mal) => {
      const s = document.createElement("script");
      s.src = "/comun/xlsx.js"; s.onload = ok; s.onerror = mal;
      document.head.appendChild(s);
    });
    return cargandoXlsx;
  }
  async function aExcel(tabla, pregunta){
    const {cab, filas} = deTabla(tabla);
    await xlsxListo();
    const euros = cab.map((_, j) => filas.some(f => /€/.test(f[j] || "")));
    const hoja = {
      nombre: "Vendi",
      titulo: [pregunta ? `Vendi · ${pregunta}` : "Vendi", `Generado el ${new Date().toLocaleString("es-ES")}`],
      columnas: cab.map((t, j) => ({titulo: t, ancho: Math.min(40, Math.max(10, t.length + 2,
                 ...filas.map(f => String(f[j] || "").length + 1))), euros: euros[j]})),
      filas: filas.map(f => f.map(c => { const n = cifra(c); return n === null ? c : n; })),
    };
    XLSX.descarga(XLSX.libro([hoja]), nombreFichero("xlsx"));
  }
  /* El PDF es la ventana de imprimir del navegador, con solo la tabla: ahi
     se elige «Guardar como PDF». Sin bibliotecas ni nada de fuera. */
  function aPdf(tabla, pregunta){
    const marco = document.createElement("iframe");
    marco.setAttribute("aria-hidden", "true");
    marco.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
    document.body.appendChild(marco);
    const doc = marco.contentDocument;
    doc.open();
    doc.write(`<!doctype html><html lang="es"><head><meta charset="utf-8"><title>${esc(nombreFichero("pdf"))}</title><style>
body{font:13px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:#0b0b0b;margin:24px}
h1{font-size:15px;margin:0 0 2px}p{margin:0 0 14px;color:#52514e;font-size:12px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th{background:#eef1f7;text-align:left;padding:8px 12px;font-weight:600;color:#3a3a37}
td{padding:8px 12px;border-top:1px solid #e2e1dc}.n{text-align:right}
tbody tr:nth-child(even) td{background:#f8f8f6}
@page{margin:14mm}</style></head><body>
<h1>${esc(pregunta ? "Vendi · " + pregunta : "Vendi")}</h1><p>Generado el ${esc(new Date().toLocaleString("es-ES"))} · dashboard.digivend.es</p>
${tabla.outerHTML}</body></html>`);
    doc.close();
    setTimeout(()=>{ try{ marco.contentWindow.focus(); marco.contentWindow.print(); }catch(e){}
                     setTimeout(()=>marco.remove(), 60000); }, 50);
  }

  const GUARDA = "digivend.asistente.hilo";
  function leeHilo(){ try{ const x = JSON.parse(sessionStorage.getItem(GUARDA) || "[]"); return Array.isArray(x) ? x.slice(-20) : []; }catch(e){ return []; } }
  function guardaHilo(h){ try{ sessionStorage.setItem(GUARDA, JSON.stringify(h.slice(-20))); }catch(e){} }
  /* El muneco se guarda en el servidor, por usuario; aqui solo se recuerda en
     la pestana para no preguntarlo en cada pagina. */
  const GUARDA_MUNECO = "digivend.asistente.muneco";
  function leeMuneco(){ try{ const m = sessionStorage.getItem(GUARDA_MUNECO); return MUNECOS[m] ? m : null; }catch(e){ return null; } }
  function guardaMuneco(m){ try{ sessionStorage.setItem(GUARDA_MUNECO, m); }catch(e){} }

  function monta(op){
    op = op || {};
    const pagina = op.pagina || "panel";
    const $ = s => document.querySelector(s);
    /* {de, texto, pregunta?}: lo que se ve en el cajon. Viene de la pagina
       anterior si la hubo; a la API solo le llegan los ultimos 6. */
    const HILO = leeHilo();
    let enVuelo = false;
    let muneco = leeMuneco() || "vendi";
    const dibujo = () => MUNECOS[muneco][2]();

    const estilo = document.createElement("style");
    estilo.textContent = CSS;
    document.head.appendChild(estilo);

    const sitio = document.createElement("div");
    sitio.innerHTML = `
<div class="as-fondo" id="fondo" hidden></div>
<aside id="chat" role="dialog" aria-modal="true" aria-label="Asistente" hidden>
  <header>
    <span id="vendiChat">${dibujo()}</span>
    <b>Asistente</b>
    <span id="chatQuedan"></span>
    <button class="btn" type="button" id="chatMuneco" title="Elige con qué muñeco sale el asistente">Muñeco</button>
    <button class="btn" type="button" id="chatMemoria" title="Lo que el asistente recuerda de ti">Memoria</button>
    <button class="btn" type="button" id="chatCerrar" aria-label="Cerrar">Cerrar</button>
  </header>
  <div class="hilo" id="hilo" aria-live="polite"></div>
  <div class="sugerencias" id="sugerencias"></div>
  <form id="chatForm">
    <textarea id="chatTexto" rows="1" placeholder="Pregunta por tus datos…" maxlength="2000"></textarea>
    <button type="submit" id="chatEnviar">Enviar</button>
  </form>
  <p class="pieChat">${esc(op.pie || "Ve lo mismo que tú en la web, nada más. No ejecuta acciones.")}</p>
</aside>
<button id="bVendi" type="button" aria-label="Preguntar al asistente">${dibujo()}</button>
<div id="bocadillo" aria-hidden="true">${esc(op.hola || "¡Hola! Pregúntame por los datos de esta página.")}</div>`;
    while(sitio.firstChild) document.body.appendChild(sitio.firstChild);

    const boton = op.boton || null;      /* el «Preguntar» de la cabecera, si la pagina lo tiene */
    if(boton){ boton.innerHTML = dibujo() + esc(boton.textContent.trim() || "Preguntar"); boton.hidden = false; }

    /* Cambia el muneco en los tres sitios a la vez y saluda con el nuevo. */
    function ponMuneco(m){
      if(!MUNECOS[m]) return;
      guardaMuneco(m);
      if(m === muneco) return;
      muneco = m;
      $("#vendiChat").innerHTML = dibujo();
      $("#bVendi").innerHTML = dibujo();
      const b = boton && boton.querySelector(".muneco");
      if(b) b.outerHTML = dibujo();
      saluda($("#vendiChat"));
    }

    function abre(abierto){
      const c = $("#chat"), f = $("#fondo");
      c.hidden = false; f.hidden = false;
      requestAnimationFrame(()=>{ c.classList.toggle("vis", abierto); f.classList.toggle("vis", abierto); });
      $("#bVendi").hidden = abierto;
      if(abierto){ $("#chatTexto").focus(); pintaSugerencias(); saluda($("#vendiChat")); $("#bocadillo").classList.remove("vis"); }
      else (boton || $("#bVendi")).focus();
    }
    function turno(de, texto, clase, preguntaDe){
      const d = document.createElement("div");
      d.className = "turno " + (clase || (de==="yo" ? "yo" : "el"));
      if(de === "yo" || clase) d.textContent = texto;
      else{
        d.innerHTML = `<span class="quien">Asistente</span>` + formatea(texto);
        d.querySelectorAll(".tabla").forEach(caja => {
          const t = caja.querySelector("table");
          caja.querySelector('[data-bajar="xlsx"]').addEventListener("click", ()=>aExcel(t, preguntaDe).catch(()=>{}));
          caja.querySelector('[data-bajar="pdf"]').addEventListener("click", ()=>aPdf(t, preguntaDe));
        });
      }
      $("#hilo").appendChild(d);
      $("#hilo").scrollTop = $("#hilo").scrollHeight;
      return d;
    }
    /* Las sugerencias las da la pagina, porque salen de lo que le ha llegado:
       a un perfil sin recaudacion no se le ofrece preguntar por la recaudacion. */
    function pintaSugerencias(){
      if(HILO.length){ $("#sugerencias").innerHTML = ""; return; }
      let q = [];
      try{ q = (op.sugerencias ? op.sugerencias() : []) || []; }catch(e){}
      $("#sugerencias").innerHTML = q.slice(0,4).map(t => `<button type="button">${esc(t)}</button>`).join("");
      $("#sugerencias").querySelectorAll("button").forEach(b => b.addEventListener("click", ()=>{
        $("#chatTexto").value = b.textContent;
        $("#chatForm").requestSubmit();
      }));
    }
    async function pregunta(texto){
      if(enVuelo || !texto) return;
      enVuelo = true;
      $("#chatEnviar").disabled = true;
      $("#sugerencias").innerHTML = "";
      turno("yo", texto);
      HILO.push({de:"usuario", texto});
      guardaHilo(HILO);
      const esperando = turno("el", "Pensando…", "el espera");
      const llama = cuerpo => fetch("/api/pregunta", {
        method:"POST", credentials:"same-origin",
        headers:{"content-type":"application/json"}, body: JSON.stringify(cuerpo),
      });
      try{
        let r = await llama({pregunta: texto, pagina,
                             historial: HILO.slice(0,-1).map(t => ({de:t.de, texto:t.texto}))});
        let d = {}; try{ d = await r.json(); }catch(e){}
        /* Por pasos: mientras el servidor diga «sigue», se le vuelve a llamar. */
        for(let i = 0; r.ok && d.sigue && i < 12; i++){
          esperando.textContent = d.estado || "Pensando…";
          r = await llama({sigue: d.sigue});
          d = {}; try{ d = await r.json(); }catch(e){}
        }
        esperando.remove();
        if(!r.ok){
          /* El motivo importa: no es lo mismo haber agotado el limite del dia
             que que el asistente este apagado para todo el mundo. */
          turno("el", d.error || (r.status === 503 || r.status === 504
            ? "El asistente ha tardado demasiado. Prueba con una pregunta más concreta."
            : "El asistente no está disponible ahora mismo."), "mal");
          HILO.pop(); guardaHilo(HILO);
          return;
        }
        if(d.muneco) ponMuneco(d.muneco);
        const t = turno("el", d.respuesta || "", null, texto);
        if(d.memoria_cambiada) t.insertAdjacentHTML("beforeend", `<span class="apuntado">Apuntado en tu memoria · pulsa «Memoria» para verla</span>`);
        HILO.push({de:"asistente", texto: d.respuesta || "", pregunta: texto});
        guardaHilo(HILO);
        if(d.quedan_hoy !== null && d.quedan_hoy !== undefined)
          $("#chatQuedan").textContent = `${d.quedan_hoy} preguntas hoy`;
      }catch(e){
        esperando.remove();
        turno("el", "No hay conexión con el servidor.", "mal");
        HILO.pop(); guardaHilo(HILO);
      }finally{
        enVuelo = false;
        $("#chatEnviar").disabled = false;
        $("#chatTexto").focus();
      }
    }

    /* Su memoria (docs/75): un Markdown por usuario que escribe Vendi cuando
       le dicen «recuerda que…». Aqui solo se ve, se baja o se vacia. */
    async function verMemoria(){
      const caja = turno("el", "Mirando tu memoria…", "el espera");
      const pide = accion => fetch("/api/pregunta", {method:"POST", credentials:"same-origin",
        headers:{"content-type":"application/json"}, body: JSON.stringify({memoria: accion})})
        .then(r => r.ok ? r.json() : Promise.reject(r));
      const pinta = md => {
        caja.className = "turno el memoria";
        caja.innerHTML = `<span class="quien">Lo que recuerdo de ti</span>` + (md
          ? formatea(md) + `<div class="acciones"><button type="button" data-m="bajar">Bajar .md</button><button type="button" data-m="borrar">Olvidarlo todo</button></div>`
          : `<p>Todavía no he apuntado nada. Dime «recuerda que…» y lo apunto aquí.</p>`);
        const b = caja.querySelector('[data-m="bajar"]');
        if(b) b.addEventListener("click", ()=>{
          const a = document.createElement("a");
          a.href = URL.createObjectURL(new Blob([md + "\n"], {type: "text/markdown;charset=utf-8"}));
          a.download = "vendi_memoria.md";
          document.body.appendChild(a); a.click();
          setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 1000);
        });
        const o = caja.querySelector('[data-m="borrar"]');
        /* Dos pulsaciones: borrar no tiene vuelta atras. */
        if(o) o.addEventListener("click", ()=>{
          if(!o.dataset.seguro){ o.dataset.seguro = "1"; o.textContent = "¿Seguro? Pulsa otra vez"; return; }
          pide("borrar").then(x => pinta(x.memoria || "")).catch(()=>{});
        });
      };
      try{ pinta((await pide("ver")).memoria || ""); }
      catch(e){ caja.className = "turno mal"; caja.textContent = "No he podido leer tu memoria ahora."; }
    }
    $("#chatMemoria").addEventListener("click", verMemoria);

    /* Elegir muneco (docs/76): los cinco, con el puesto marcado. Como la
       memoria, no es una pregunta y no se guarda en la conversacion. */
    function verMunecos(){
      const caja = turno("el", "", "el munecos");
      caja.innerHTML = `<span class="quien">Elige con quién sales</span><p>También me lo puedes pedir escribiendo, por ejemplo «ponme a Bufy».</p><div class="lista">` +
        Object.entries(MUNECOS).map(([id, [nombre, que, f]]) =>
          `<button type="button" data-muneco="${id}" aria-pressed="${id === muneco}">${f()}<b>${esc(nombre)}</b><span>${esc(que)}</span></button>`).join("") + `</div>`;
      caja.querySelectorAll("[data-muneco]").forEach(b => {
        b.addEventListener("mouseenter", ()=>saluda(b));
        b.addEventListener("click", async ()=>{
          const m = b.dataset.muneco;
          try{
            const r = await fetch("/api/pregunta", {method:"POST", credentials:"same-origin",
              headers:{"content-type":"application/json"}, body: JSON.stringify({muneco: m})});
            if(!r.ok) throw r;
            ponMuneco(m);
            caja.querySelectorAll("[data-muneco]").forEach(x => x.setAttribute("aria-pressed", String(x.dataset.muneco === m)));
          }catch(e){
            if(!caja.querySelector(".apuntado")) caja.insertAdjacentHTML("beforeend", `<span class="apuntado">No he podido cambiarlo ahora. Prueba otra vez.</span>`);
          }
        });
      });
    }
    $("#chatMuneco").addEventListener("click", verMunecos);

    /* La conversacion de la pagina anterior, tal cual se dejo. */
    HILO.forEach(t => t.de === "usuario" ? turno("yo", t.texto) : turno("el", t.texto, null, t.pregunta));
    /* Al salir de la sesion no se queda nada: otro usuario en esta pestana
       no veria lo que se pregunto. */
    const salir = document.querySelector("#bSalir");
    if(salir) salir.addEventListener("click", ()=>{ try{ sessionStorage.removeItem(GUARDA); sessionStorage.removeItem(GUARDA_MUNECO); }catch(e){} }, true);

    if(boton) boton.addEventListener("click", ()=>abre(true));
    $("#bVendi").addEventListener("click", ()=>abre(true));
    $("#bVendi").addEventListener("mouseenter", ()=>saluda($("#bVendi")));
    $("#chatCerrar").addEventListener("click", ()=>abre(false));
    $("#fondo").addEventListener("click", ()=>abre(false));
    addEventListener("keydown", e=>{ if(e.key==="Escape" && $("#chat").classList.contains("vis")) abre(false); });
    $("#chatForm").addEventListener("submit", e=>{
      e.preventDefault();
      const t = $("#chatTexto").value.trim();
      $("#chatTexto").value = ""; $("#chatTexto").style.height = "";
      pregunta(t);
    });
    $("#chatTexto").addEventListener("input", e=>{
      e.target.style.height = "auto";
      e.target.style.height = Math.min(140, e.target.scrollHeight) + "px";
    });
    $("#chatTexto").addEventListener("keydown", e=>{
      /* Enter envia; Mayus+Enter hace parrafo. Es lo que espera quien escribe rapido. */
      if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); $("#chatForm").requestSubmit(); }
    });

    /* El muneco de este usuario, una vez por pestana. El servidor dice ademas
       si toca recordarle que puede cambiarlo: un dia distinto cada vez y tres
       veces como mucho, y nunca si ya eligio. */
    const aviso = leeMuneco() ? Promise.resolve(false) :
      fetch("/api/pregunta", {method:"POST", credentials:"same-origin",
        headers:{"content-type":"application/json"}, body: JSON.stringify({muneco: "ver"})})
        .then(r => r.ok ? r.json() : {}).then(d => { ponMuneco(d.muneco || "vendi"); return !!d.avisar; })
        .catch(() => false);

    /* Al entrar, el muneco saluda y dice hola unos segundos. Si la pagina esta
       con su bienvenida animada, espera a que acabe: debajo no lo veria nadie. */
    function hola(){
      const espera = new Promise(ok => setTimeout(()=>ok(false), 1500));
      setTimeout(async ()=>{
        const avisar = await Promise.race([aviso, espera]);
        if(avisar) $("#bocadillo").textContent = "¡Hola! Ahora puedo salir con otro muñeco: Tom, Kiko, Furgo o Bufy. " +
          "Ábreme y pulsa «Muñeco», o pídemelo escribiendo.";
        saluda($("#bVendi"));
        $("#bocadillo").classList.add("vis");
        setTimeout(()=>$("#bocadillo").classList.remove("vis"), avisar ? 9000 : 4500);
      }, 700);
    }
    const raiz = document.documentElement;
    if(raiz.classList.contains("bienvenida")){
      const ob = new MutationObserver(()=>{
        if(!raiz.classList.contains("bienvenida")){ ob.disconnect(); hola(); }
      });
      ob.observe(raiz, {attributes:true, attributeFilter:["class"]});
    }else hola();

    return {abre};
  }

  /* Las secciones (rutas, incidencias…) no montan nada a mano: cargan este
     fichero con data-pagina y Vendi sale solo si la sesion tiene el
     asistente (docs/71). El panel y el informe general lo montan ellos, con
     su boton «Preguntar» y sus sugerencias. */
  const SECCION = {
    rutas: ["las rutas", ["¿Qué delegación cumplió peor las rutas ayer?", "¿Qué máquinas llevan más días sin reponer?"]],
    incidencias: ["las incidencias", ["¿Cuántas averías se cerraron en menos de 24 h esta semana?", "¿Qué área tiene más incidencias abiertas?"]],
    devoluciones: ["las devoluciones", ["¿Cuánto se ha devuelto este mes y por qué motivo?", "¿Qué centros acumulan más devoluciones?"]],
    furgonetas: ["las furgonetas", ["¿Qué furgonetas no tuvieron visitas ayer?", "¿Cuántos km se hicieron ayer por área?"]],
    almacenes: ["los almacenes", ["¿Qué almacenes tienen más artículos bajo mínimo?", "¿Cuándo fue el último pedido de cada almacén?"]],
    telemetria: ["la telemetría", ["¿Cuántas máquinas tienen telemetría por sistema?", "¿Dónde hay más diferencias con VenCloud?"]],
    tarifas: ["las tarifas", ["¿Qué centros cobran precios distintos a su tarifa?", "¿Cuántos productos venden sin tarifa?"]],
    revision: ["la revisión de clientes", ["¿Cuántas máquinas no tienen planograma?", "¿Qué delegación tiene más precios distintos?"]],
    utilizo: ["el uso de VenCloud", ["¿Quién usó más VenCloud este mes?", "¿Quién lleva más días sin entrar?"]],
    preferidos: ["tus preferidos", ["Resúmeme mis preferidos de ayer."]],
  };
  const yo = document.currentScript && document.currentScript.dataset.pagina;
  if(yo){
    const sola = async () => {
      let d = null;
      try{ const r = await fetch("/api/yo", {credentials:"same-origin", headers:{"x-digivend-vista":"no"}}); if(r.ok) d = await r.json(); }catch(e){}
      if(!d || !d.asistente || !d.asistente.habilitado) return;
      const [de, sug] = SECCION[yo] || ["esta página", []];
      monta({pagina: yo, hola: `¡Hola! Pregúntame por ${de} o por cualquier sección que veas.`, sugerencias: () => sug});
    };
    if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", sola); else sola();
  }

  window.Asistente = {monta, vendi, formatea, MUNECOS};
})();
