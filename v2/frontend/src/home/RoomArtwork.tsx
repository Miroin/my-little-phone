export function LivingRoomArtwork({fireOn}:{fireOn:boolean}){return <div className="room-artwork living-painterly-art" aria-hidden="true">
  <img className="living-perspective-review" src="./home-assets/rooms/living-v2/living-perspective-review.png" alt=""/>
  <img className="living-painterly-background" src="./home-assets/rooms/living-v2/living-background.png" alt=""/>
  <img className="living-asset living-tv-asset" src="./home-assets/rooms/living-v2/media-console.png" alt=""/>
  <img className="living-asset living-console-asset" src="./home-assets/rooms/living-v2/media-console.png" alt=""/>
  <img className="living-asset living-fireplace-asset" src="./home-assets/rooms/living-v2/fireplace.png" alt=""/>
  <img className="living-asset living-record-asset" src="./home-assets/rooms/living-v2/record-corner.png" alt=""/>
  <img className="living-asset living-sofa-asset" src="./home-assets/rooms/living-v2/sofa.png" alt=""/>
  <img className="living-asset living-table-asset" src="./home-assets/rooms/living-v2/coffee-table.png" alt=""/>
  <span className={`living-painterly-fire ${fireOn?'is-on':'is-off'}`}/>
  <span className="living-painterly-light"/>
</div>}

function LegacyLivingRoomArtwork({fireOn}:{fireOn:boolean}){return <svg className="room-artwork" viewBox="0 0 1000 650" preserveAspectRatio="none" aria-hidden="true">
  <defs>
    <linearGradient id="lr-wall" x2="0" y2="1"><stop stopColor="#f3eee8"/><stop offset="1" stopColor="#e7ddd5"/></linearGradient>
    <linearGradient id="lr-floor" x2="0" y2="1"><stop stopColor="#cdb394"/><stop offset="1" stopColor="#aa876b"/></linearGradient>
    <linearGradient id="lr-sofa" x2="0" y2="1"><stop stopColor="#f2ebe4"/><stop offset="1" stopColor="#d8cec8"/></linearGradient>
    <linearGradient id="lr-wood" x2="1"><stop stopColor="#c6a782"/><stop offset="1" stopColor="#876b58"/></linearGradient>
    <filter id="lr-shadow"><feDropShadow dx="0" dy="10" stdDeviation="10" floodColor="#493b3f" floodOpacity=".22"/></filter>
  </defs>
  <rect width="1000" height="440" fill="url(#lr-wall)"/><rect y="440" width="1000" height="210" fill="url(#lr-floor)"/>
  <g opacity=".18" stroke="#9d888e"><path d="M0 55H1000M0 390H1000"/><path d="M90 55V390M315 55V390M690 55V390M910 55V390"/></g>
  <path d="M0 440H1000" stroke="#876b58" strokeWidth="16"/><g opacity=".18" stroke="#765844"><path d="M70 440L30 650M200 440L185 650M340 440L350 650M500 440L520 650M670 440L700 650M840 440L900 650"/></g>
  <g filter="url(#lr-shadow)">
    <path d="M695 45h225a18 18 0 0 1 18 18v235H677V63a18 18 0 0 1 18-18Z" fill="#f7f1e9" stroke="#c9b49f" strokeWidth="12"/>
    <rect x="700" y="68" width="215" height="205" rx="4" fill="#aebfca"/><circle cx="862" cy="117" r="36" fill="#f4dfaf" opacity=".9"/>
    <path d="M807 68v205M700 170h215" stroke="#eee6dc" strokeWidth="8"/>
    <path d="M677 42q28 17 31 55v206h-47V72q0-22 16-30Zm261 0q-28 17-31 55v206h47V72q0-22-16-30Z" fill="#a998ad"/>
    <path d="M670 46v257M945 46v257" stroke="#d6c5d9" strokeWidth="9" opacity=".65"/>
  </g>
  <g filter="url(#lr-shadow)">
    <rect x="350" y="80" width="270" height="164" rx="9" fill="#876b58"/><rect x="365" y="95" width="240" height="134" rx="4" fill="#29282d"/>
    <path d="M382 104h205" stroke="#676271" strokeWidth="5" opacity=".55"/><rect x="326" y="250" width="318" height="74" rx="6" fill="url(#lr-wood)"/>
    <rect x="342" y="267" width="92" height="40" rx="3" fill="#b89472" stroke="#876b58"/><rect x="446" y="267" width="74" height="40" rx="3" fill="#b89472" stroke="#876b58"/><rect x="532" y="267" width="96" height="40" rx="3" fill="#b89472" stroke="#876b58"/>
    <circle cx="423" cy="287" r="4" fill="#aa8b65"/><circle cx="508" cy="287" r="4" fill="#aa8b65"/><circle cx="546" cy="287" r="4" fill="#aa8b65"/>
  </g>
  <g filter="url(#lr-shadow)">
    <path d="M35 105h185v330H35Z" fill="#876b58"/><path d="M52 123h151v294H52Z" fill="#b99472"/>
    <path d="M52 218h151M52 316h151" stroke="#745644" strokeWidth="9"/>
    <g fill="#d8bea0"><rect x="63" y="139" width="15" height="69"/><rect x="84" y="151" width="18" height="57"/><rect x="109" y="133" width="12" height="75"/><rect x="128" y="158" width="20" height="50"/><rect x="156" y="141" width="14" height="67"/><rect x="177" y="149" width="15" height="59"/></g>
    <g fill="#7a6572"><rect x="62" y="235" width="19" height="70"/><rect x="89" y="248" width="13" height="57"/><rect x="110" y="228" width="17" height="77"/><rect x="136" y="241" width="20" height="64"/></g>
    <rect x="60" y="340" width="65" height="42" rx="3" fill="#d2b895"/><path d="M150 382q25-72 45 0Z" fill="#8d9c83"/>
  </g>
  <g filter="url(#lr-shadow)">
    <path d="M238 306h135v124H238Z" fill="#e5ddd4"/><path d="M220 296h171v22H220Z" fill="#aa8b65"/>
    <path d="M260 344q0-35 44-35t44 35v76h-88Z" fill="#4a3b3a"/>
    {fireOn&&<path d="M284 404q-22-35 11-65-4 31 18 40 15-30 22-50 24 43-4 77-20 22-47-2Z" fill="#e9894d" stroke="#f6d59a" strokeWidth="8"/>}
  </g>
  <ellipse cx="574" cy="566" rx="287" ry="79" fill="#d6c5d9" opacity=".72"/>
  <g filter="url(#lr-shadow)">
    <path d="M364 382q0-59 64-59h284q64 0 64 59v145H364Z" fill="url(#lr-sofa)" stroke="#b8a8aa" strokeWidth="7"/>
    <path d="M380 393q0-36 34-36h34v153h-68Z" fill="#ded4d0"/><path d="M692 357h34q34 0 34 36v117h-68Z" fill="#ded4d0"/>
    <path d="M448 352h91v157h-91Z" fill="#eee6df" stroke="#c8bcb8"/><path d="M539 352h91v157h-91Z" fill="#eee6df" stroke="#c8bcb8"/><path d="M630 352h62v157h-62Z" fill="#e8dfd9" stroke="#c8bcb8"/>
    <path d="M382 474h376v58H382Z" fill="#c9beb9"/><path d="M407 531v22M730 531v22" stroke="#876b58" strokeWidth="13"/>
    <path d="M425 369q28-22 56 0v61h-56Z" fill="#d6c5d9" stroke="#aa99af"/><path d="M651 371q28-22 56 0v58h-56Z" fill="#a998ad" stroke="#89788f"/>
    <g stroke="#b6aaa6" opacity=".5"><path d="M464 376v109M555 376v109M646 376v109"/></g>
  </g>
  <g filter="url(#lr-shadow)">
    <ellipse cx="566" cy="574" rx="137" ry="40" fill="#6d4f3f" opacity=".25"/><path d="M453 535q113-26 226 0v45q-113 26-226 0Z" fill="#c6a782" stroke="#876b58" strokeWidth="6"/>
    <path d="M482 577l-18 58M650 577l18 58" stroke="#876b58" strokeWidth="10"/><rect x="518" y="521" width="60" height="13" rx="3" fill="#f1e9de"/><circle cx="611" cy="527" r="12" fill="#d6c5d9"/>
  </g>
  <g filter="url(#lr-shadow)"><path d="M823 350v172" stroke="#876b58" strokeWidth="9"/><path d="M775 341q48-58 96 0Z" fill="#ddd0b3"/><ellipse cx="823" cy="526" rx="43" ry="10" fill="#876b58"/></g>
  <g><path d="M905 484q-45-74 0-103 28 34 0 103Z" fill="#8d9c83"/><path d="M923 484q18-93 55-65-2 48-55 65Z" fill="#74866d"/><path d="M895 488h75l-13 68h-49Z" fill="#aa8b65"/></g>
  <g filter="url(#lr-shadow)"><rect x="823" y="515" width="135" height="111" rx="4" fill="url(#lr-wood)"/><circle cx="888" cy="559" r="43" fill="#242328"/><circle cx="888" cy="559" r="7" fill="#c6a782"/><rect x="841" y="585" width="98" height="24" rx="3" fill="#9a775e"/></g>
  <g transform="translate(258 372) rotate(-7)"><rect width="60" height="82" rx="3" fill="#876b58"/><rect x="8" y="8" width="44" height="66" fill="#d6c5d9"/><path d="M15 61q17-24 34 0" stroke="#aa8b65" strokeWidth="5" fill="none"/></g>
 </svg>}

export function BedroomArtwork({lightsOn,curtainsClosed,bedActivity}:{lightsOn:boolean;curtainsClosed:boolean;bedActivity:'idle'|'sitting'|'lying'}){return <svg className="room-artwork" viewBox="0 0 1000 650" preserveAspectRatio="none" aria-hidden="true">
  <defs><linearGradient id="br-wall" x2="0" y2="1"><stop stopColor="#f2ede8"/><stop offset="1" stopColor="#e6dce2"/></linearGradient><linearGradient id="br-floor" x2="0" y2="1"><stop stopColor="#c5aa8d"/><stop offset="1" stopColor="#a78368"/></linearGradient><linearGradient id="br-bed" x2="0" y2="1"><stop stopColor="#eee7e2"/><stop offset="1" stopColor="#d6cbd2"/></linearGradient><filter id="br-shadow"><feDropShadow dx="0" dy="10" stdDeviation="9" floodColor="#493c45" floodOpacity=".22"/></filter></defs>
  <rect width="1000" height="438" fill="url(#br-wall)"/><rect y="438" width="1000" height="212" fill="url(#br-floor)"/><path d="M0 438H1000" stroke="#876b58" strokeWidth="15"/>
  <g opacity=".18" stroke="#a998ad"><rect x="38" y="45" width="924" height="332" rx="5"/><path d="M250 45v332M750 45v332"/></g><g opacity=".16" stroke="#765844"><path d="M80 438L35 650M220 438L205 650M380 438L390 650M550 438L575 650M720 438L765 650M890 438L965 650"/></g>
  <g filter="url(#br-shadow)"><path d="M686 38q0-28 28-28h169q28 0 28 28v256H686Z" fill="#f7f1e9" stroke="#c6a782" strokeWidth="9"/><path d="M708 54q0-22 22-22h137q22 0 22 22v217H708Z" fill="#8fa7b8"/><circle cx="841" cy="92" r="34" fill="#e8e2c9"/><path d="M798 34v237M708 151h181" stroke="#efe7dc" strokeWidth="7"/><path d="M702 270h193" stroke="#876b58" strokeWidth="13"/>
    <path d={curtainsClosed?'M671 25h118v270H660V52q0-18 11-27Z':'M671 25h49v270H660V52q0-18 11-27Z'} fill="#a998ad" opacity=".96"/><path d={curtainsClosed?'M806 25h105q14 9 14 27v243H795V25Z':'M875 25h36q14 9 14 27v243h-50V25Z'} fill="#a998ad" opacity=".96"/><g stroke="#d6c5d9" strokeWidth="7" opacity=".55"><path d="M682 31v257M705 31v257M895 31v257M914 31v257"/></g></g>
  <g filter="url(#br-shadow)"><rect x="60" y="104" width="120" height="150" rx="3" fill="#f7f1e9" stroke="#c6a782" strokeWidth="7"/><rect x="78" y="122" width="84" height="114" fill="#d6c5d9"/><path d="M91 218q29-56 58 0" fill="#a998ad"/><rect x="196" y="91" width="106" height="132" rx="3" fill="#f7f1e9" stroke="#c6a782" strokeWidth="7"/><rect x="214" y="109" width="70" height="96" fill="#ddd4cf"/></g>
  <ellipse cx="514" cy="576" rx="328" ry="64" fill="#d6c5d9" opacity=".75"/>
  <g filter="url(#br-shadow)"><path d="M235 319q0-92 92-92h381q92 0 92 92v228H235Z" fill="#a998ad" stroke="#876b58" strokeWidth="8"/><path d="M265 315q0-59 63-59h380q62 0 62 59v59H265Z" fill="#b7a6bb"/>
    <g fill="#d6c5d9" stroke="#8e7c92"><path d="M286 305q0-28 28-28h76q28 0 28 28v54H286Z"/><path d="M429 305q0-28 28-28h76q28 0 28 28v54H429Z"/><path d="M572 305q0-28 28-28h76q28 0 28 28v54H572Z"/><path d="M715 309q0-25 24-25h11v75h-35Z"/></g>
    <rect x="258" y="360" width="519" height="190" rx="22" fill="url(#br-bed)" stroke="#c4b7bd" strokeWidth="7"/>
    <g><path d="M286 377q93-33 174 0v63q-88 25-174 0Z" fill="#f7f1e9" stroke="#d5cbc5"/><path d="M475 377q91-32 181 0v63q-90 25-181 0Z" fill="#f7f1e9" stroke="#d5cbc5"/><path d="M666 384q51-21 81 1v55q-42 18-81 0Z" fill="#ddd4cf"/></g>
    <path d={bedActivity==='lying'?'M272 435q80-30 160 2 90-35 178 0 77-22 153 4v104H272Z':bedActivity==='sitting'?'M272 441q78-22 153 5 78-35 161 0 83-22 177 2v97H272Z':'M272 436q82-20 161 3 81-28 163 0 79-17 167 2v104H272Z'} fill="#d6c5d9" stroke="#bbaabe" strokeWidth="4"/>
    <g stroke="#b9a8bc" strokeWidth="3" opacity=".55"><path d="M330 453q-13 42 4 80M440 451q11 45-3 83M557 451q-8 43 5 82M677 453q12 40-4 79" fill="none"/></g>
    <path d="M273 509h490v42H273Z" fill="#b9a5bb"/><path d="M287 551v17M749 551v17" stroke="#876b58" strokeWidth="14"/>
  </g>
  <g filter="url(#br-shadow)"><g transform="translate(63 392)"><rect width="145" height="149" rx="5" fill="#c6a782"/><rect x="17" y="20" width="111" height="50" rx="3" fill="#b58e6d" stroke="#876b58"/><rect x="17" y="81" width="111" height="50" rx="3" fill="#b58e6d" stroke="#876b58"/><circle cx="73" cy="45" r="5" fill="#aa8b65"/><circle cx="73" cy="106" r="5" fill="#aa8b65"/></g><g transform="translate(806 392)"><rect width="130" height="149" rx="5" fill="#c6a782"/><rect x="15" y="20" width="100" height="50" rx="3" fill="#b58e6d" stroke="#876b58"/><rect x="15" y="81" width="100" height="50" rx="3" fill="#b58e6d" stroke="#876b58"/><circle cx="65" cy="45" r="5" fill="#aa8b65"/><circle cx="65" cy="106" r="5" fill="#aa8b65"/></g></g>
  <g opacity={lightsOn?1:.45}><path d="M134 389v-79" stroke="#876b58" strokeWidth="7"/><path d="M91 313q43-58 86 0Z" fill="#e5d3aa"/>{lightsOn&&<ellipse cx="134" cy="310" rx="66" ry="48" fill="#f3dca0" opacity=".18"/>}<path d="M870 389v-79" stroke="#876b58" strokeWidth="7"/><path d="M827 313q43-58 86 0Z" fill="#e5d3aa"/>{lightsOn&&<ellipse cx="870" cy="310" rx="66" ry="48" fill="#f3dca0" opacity=".18"/>}</g>
  <g filter="url(#br-shadow)"><rect x="304" y="569" width="410" height="55" rx="22" fill="#a998ad"/><path d="M330 622v18M688 622v18" stroke="#876b58" strokeWidth="10"/><rect x="838" y="367" width="67" height="17" rx="3" fill="#876b58" transform="rotate(6 838 367)"/><path d="M846 366h52" stroke="#f0eae5" strokeWidth="5"/></g>
 </svg>}
