// Tela de escolha "O que você quer fazer?" (📚 Aprender / 🎨 Passatempo / 🎮 Jogar).
// Depois da escolha, a grade (launcher-ui.js) mostra só os tiles da categoria.
// Os tempos vêm de /api/usage/status (usage-limits.js: usageStatus, usageCategory...).
const ESCOLHA_RETORNO_KEY='cozyEscolhaRetornoV1';
const ESCOLHA_RETORNO_VALIDADE_MS=6*60*60*1000;
const ESCOLHA_OPCOES=[
  {id:'educativo',titulo:'Aprender',emoji:'📚',lista:'Aprender'},
  {id:'passatempo',titulo:'Passatempo',emoji:'🎨',lista:'Passatempo'},
  {id:'jogos',titulo:'Jogar',emoji:'🎮',lista:'Jogar'}
];
// Passatempo só aparece se o perfil tiver essa categoria (nos limites ou em algum tile).
function escolhaTemPassatempo(){
  if(typeof usageStatus==='undefined'||!usageStatus) return false;
  if((usageStatus.categories||[]).some(c=>c.id==='passatempo')) return true;
  return Object.values(usageStatus.tileCategories||{}).includes('passatempo');
}
function escolhaOpcoes(){ return ESCOLHA_OPCOES.filter(o=>o.id!=='passatempo'||escolhaTemPassatempo()); }
let escolhaModo=null;      // null = tela de escolha; 'educativo' | 'jogos' = lista filtrada
let escolhaPerfil=null;    // perfil para o qual a escolha vale
let escolhaAssinatura='';  // evita redesenhar sem necessidade a cada poll de uso

function escolhaHabilitada(){ return !!cfg&&cfg.choiceScreenEnabled!==false; }
function escolhaSincronizarPerfil(){
  const perfil=(cfg&&cfg.activeProfileId)||'default';
  if(escolhaPerfil!==perfil){ escolhaPerfil=perfil; escolhaModo=null; }
}
function escolhaNaTela(){ if(!escolhaHabilitada()) return false; escolhaSincronizarPerfil(); return !escolhaModo; }
function escolhaNaLista(){ if(!escolhaHabilitada()) return false; escolhaSincronizarPerfil(); return !!escolhaModo; }
function escolhaOpcao(id){ return escolhaOpcoes().find(o=>o.id===id)||null; }

// Categoria efetiva: o servidor já aplica a regra padrão de usage_limits.py
// para tiles sem o campo "category" (usageStatus.tileCategories).
function escolhaCategoriaDoTile(tile){
  const mapa=typeof usageStatus!=='undefined'&&usageStatus&&usageStatus.tileCategories;
  if(mapa&&Object.prototype.hasOwnProperty.call(mapa,tile.id)) return mapa[tile.id]||'';
  return tile.category||'';
}
// "Aprender" = educativo; "Passatempo" = passatempo; "Jogar" = todo o resto (jogos, sem categoria, outras).
function escolhaTileNaLista(tile){
  if(!escolhaNaLista()) return true;
  const categoria=escolhaCategoriaDoTile(tile);
  if(escolhaModo==='educativo'||escolhaModo==='passatempo') return categoria===escolhaModo;
  const proprias=escolhaTemPassatempo()?['educativo','passatempo']:['educativo'];
  return !proprias.includes(categoria);
}

// Tempo da categoria: {comTempo, esgotada, restante (s), limite (s)}
function escolhaTempo(id){
  const vazio={comTempo:false,esgotada:false,restante:null,limite:null};
  if(typeof usageStatus==='undefined'||!usageStatus||!usageStatus.enabled) return vazio;
  const cat=usageCategory(id);
  const totalLimite=usageStatus.totalMinutes===null||usageStatus.totalMinutes===undefined?null:usageStatus.totalMinutes*60;
  if(!cat){
    if(totalLimite===null) return vazio;
    const restante=usageStatus.totalRemainingSeconds||0;
    return {comTempo:true,esgotada:!!usageStatus.totalExhausted,restante,limite:totalLimite};
  }
  const esgotada=!!(cat.exhausted||usageStatus.totalExhausted);
  if(cat.availableSeconds===null||cat.availableSeconds===undefined) return {...vazio,esgotada};
  const limite=cat.minutes===null||cat.minutes===undefined?totalLimite:cat.minutes*60;
  return {comTempo:true,esgotada,restante:cat.availableSeconds,limite:limite||cat.availableSeconds||1};
}
function escolhaTextoTempo(t){
  if(t.esgotada) return 'Amanhã tem mais!';
  if(!t.comTempo) return '';
  const min=usageMinutes(t.restante);
  return min<=1?'falta 1 min':'faltam '+min+' min';
}
function escolhaBarra(t){
  const barra=document.createElement('span');
  barra.className='escolha-barra';
  const fill=document.createElement('span');
  fill.className='escolha-barra-fill escolha-'+(t.esgotada?'out':usageBand(t.restante,t.limite));
  const fracao=t.esgotada?0:Math.max(0,Math.min(1,(t.restante||0)/(t.limite||1)));
  fill.style.width=Math.round(fracao*100)+'%';
  barra.appendChild(fill);
  return barra;
}

function escolhaPodeFocar(){
  const msg=document.getElementById('usageMessage');
  if(msg&&!msg.classList.contains('hidden')) return false;
  return typeof homeGestureAllowed!=='function'||homeGestureAllowed();
}

// Chamado por renderKids(): desenha a escolha e devolve true, ou false para a lista normal.
function renderEscolha(grid){
  const naTela=escolhaNaTela();
  document.body.classList.toggle('escolha-ativa',naTela);
  escolhaAtualizarBarra();
  if(!naTela) return false;
  const opcoes=escolhaOpcoes();
  grid.className='grid escolha-grid escolha-n'+opcoes.length;
  const pergunta=document.createElement('h1');
  pergunta.className='escolha-pergunta';
  pergunta.setAttribute('aria-level','2');
  pergunta.textContent='O que você quer fazer?';
  grid.appendChild(pergunta);
  opcoes.forEach((opcao,i)=>grid.appendChild(escolhaBotao(opcao,i)));
  if(focusedTileIndex>=opcoes.length) focusedTileIndex=0;
  updateTileFocus(escolhaPodeFocar());
  escolhaAssinatura=escolhaCalcularAssinatura();
  return true;
}
function escolhaBotao(opcao,indice){
  const t=escolhaTempo(opcao.id);
  const btn=document.createElement('button');
  btn.type='button';
  btn.className='tile escolha-btn escolha-'+opcao.id+(t.esgotada?' escolha-bloqueada':'');
  btn.dataset.escolha=opcao.id;
  btn.style.position='relative';
  const textoTempo=escolhaTextoTempo(t);
  btn.setAttribute('aria-label',opcao.titulo+(textoTempo?', '+textoTempo:''));
  if(t.esgotada) btn.setAttribute('aria-disabled','true');
  const emoji=document.createElement('span');
  emoji.className='escolha-emoji';
  emoji.textContent=opcao.emoji;
  if(t.esgotada){
    const cadeado=document.createElement('span');
    cadeado.className='escolha-cadeado';
    cadeado.textContent='🔒';
    emoji.appendChild(cadeado);
  }
  const nome=document.createElement('span');
  nome.className='escolha-nome';
  nome.textContent=opcao.titulo;
  btn.append(emoji,nome);
  if(t.comTempo||t.esgotada){
    const tempo=document.createElement('span');
    tempo.className='escolha-tempo';
    if(t.comTempo&&!t.esgotada) tempo.appendChild(escolhaBarra(t));
    const txt=document.createElement('span');
    txt.className='escolha-tempo-texto';
    txt.textContent=textoTempo;
    tempo.appendChild(txt);
    btn.appendChild(tempo);
  }
  btn.onfocus=()=>{ focusedTileIndex=indice; updateTileFocus(false); };
  btn.onclick=event=>{
    if(typeof tileClickSuppressed==='function'&&tileClickSuppressed(event)) return;
    if(escolhaTempo(opcao.id).esgotada){
      playFeedbackSound('blocked');
      replayMotionClass(btn,'escolha-balanca',500);
      const [titulo,corpo]=usageLimitTexts(usageStatus&&usageStatus.totalExhausted?'daily_limit':'category_limit',opcao.id);
      showUsageMessage(titulo,corpo);
      return;
    }
    escolhaEntrar(opcao.id);
  };
  return btn;
}

function escolhaEntrar(id){
  if(!escolhaOpcao(id)) return;
  escolhaSincronizarPerfil();
  escolhaModo=id;
  cfg.currentPage=0;
  focusedTileIndex=0;
  playFeedbackSound('navigate');
  renderAll();
  playLauncherPageTransition(1);
}
function escolhaVoltar(){
  if(!escolhaNaLista()) return;
  const anterior=escolhaOpcoes().findIndex(o=>o.id===escolhaModo);
  escolhaModo=null;
  cfg.currentPage=0;
  focusedTileIndex=Math.max(0,anterior);
  playFeedbackSound('navigate');
  renderAll();
  playLauncherPageTransition(-1);
}

// Barra do topo na lista: "⬅ Voltar" + categoria com o tempo restante.
function escolhaAtualizarBarra(){
  const voltar=document.getElementById('escolhaVoltar');
  const chip=document.getElementById('escolhaChip');
  if(!voltar||!chip) return;
  const naLista=escolhaNaLista();
  voltar.hidden=!naLista;
  chip.hidden=!naLista;
  document.body.classList.toggle('escolha-lista',naLista);
  if(!naLista){ chip.replaceChildren(); return; }
  const opcao=escolhaOpcao(escolhaModo);
  const t=escolhaTempo(escolhaModo);
  chip.className='smallbtn escolha-chip'+(t.esgotada?' escolha-bloqueada':'');
  const emoji=document.createElement('span');
  emoji.className='escolha-chip-emoji';
  emoji.textContent=t.esgotada?'🔒':opcao.emoji;
  const corpo=document.createElement('span');
  corpo.className='escolha-chip-corpo';
  const nome=document.createElement('span');
  nome.className='escolha-chip-nome';
  nome.textContent=opcao.lista;
  corpo.appendChild(nome);
  if(t.comTempo&&!t.esgotada) corpo.appendChild(escolhaBarra(t));
  chip.replaceChildren(emoji,corpo);
  const texto=escolhaTextoTempo(t);
  if(texto){
    const txt=document.createElement('span');
    txt.className='escolha-chip-tempo';
    txt.textContent=t.esgotada?'acabou':texto;
    chip.appendChild(txt);
  }
  chip.setAttribute('aria-label',opcao.lista+(texto?', '+texto:''));
}

function escolhaCalcularAssinatura(){
  const partes=escolhaOpcoes().map(o=>{ const t=escolhaTempo(o.id); return [o.id,t.comTempo,t.esgotada,t.comTempo?usageMinutes(t.restante):'',t.limite].join(':'); });
  const mapa=typeof usageStatus!=='undefined'&&usageStatus&&usageStatus.tileCategories;
  partes.push(mapa?JSON.stringify(mapa):'');
  return partes.join('|');
}
// Chamado por pollUsage() (usage-limits.js) a cada atualização de uso.
function escolhaOnUsage(){
  if(!cfg||!escolhaHabilitada()) return;
  if(!document.getElementById('admin').classList.contains('hidden')) return;
  const assinatura=escolhaCalcularAssinatura();
  if(assinatura===escolhaAssinatura) return;
  const categoriasMudaram=assinatura.split('|').pop()!==escolhaAssinatura.split('|').pop();
  escolhaAssinatura=assinatura;
  if(escolhaNaLista()&&escolhaTempo(escolhaModo).esgotada){
    // A categoria acabou: volta para a escolha, onde ela aparece bloqueada.
    escolhaModo=null;
    cfg.currentPage=0;
    renderAll();
    return;
  }
  if(escolhaNaTela()){ renderKids(); return; }
  if(categoriasMudaram){ renderAll(); return; }
  escolhaAtualizarBarra();
}

// Ao sair da página para um site/biblioteca de mídia, guarda a lista atual
// para voltar a ela; ao reabrir o launcher (sem esse marcador) aparece a escolha.
function escolhaLembrarRetorno(){
  if(!escolhaNaLista()) return;
  try{
    sessionStorage.setItem(ESCOLHA_RETORNO_KEY,JSON.stringify({
      profileId:escolhaPerfil,mode:escolhaModo,page:cfg.currentPage||0,at:Date.now()
    }));
  }catch(e){}
}
function escolhaRestaurarRetorno(){
  let dados=null;
  try{
    const raw=sessionStorage.getItem(ESCOLHA_RETORNO_KEY);
    sessionStorage.removeItem(ESCOLHA_RETORNO_KEY);
    dados=raw&&raw.length<300?JSON.parse(raw):null;
  }catch(e){ return; }
  if(!dados||!escolhaOpcao(dados.mode)||typeof dados.profileId!=='string') return;
  if(!(Date.now()-Number(dados.at)<ESCOLHA_RETORNO_VALIDADE_MS)) return;
  escolhaPerfil=dados.profileId;
  escolhaModo=dados.mode;
  escolhaPaginaRetorno=Math.max(0,parseInt(dados.page,10)||0);
}
let escolhaPaginaRetorno=null;
// Aplicada depois de loadConfig (a página guardada vale para a lista filtrada).
function escolhaAplicarPaginaRetorno(){
  if(escolhaPaginaRetorno===null||!cfg) return;
  if(escolhaNaLista()) cfg.currentPage=escolhaPaginaRetorno;
  escolhaPaginaRetorno=null;
}
escolhaRestaurarRetorno();
