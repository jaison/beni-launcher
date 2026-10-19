// Limites diários por categoria (Jogos / Aprender / Passatempo): medidores para a criança,
// mensagem amigável quando o tempo acaba e configuração no painel dos pais.
let usageStatus=null, usagePollInterval=null, usageLastExpiryShown=0, usageMessageTimer=null;
try{ usageLastExpiryShown=Number(sessionStorage.getItem('cozyUsageExpiryShown'))||0; }catch(e){}

function usageMinutes(seconds){ return Math.max(0,Math.ceil((Number(seconds)||0)/60)); }
function usageUsedMinutes(seconds){ return Math.max(0,Math.floor((Number(seconds)||0)/60)); }
function usageBand(available,limitSeconds){
  if(available===null||available===undefined) return 'ok';
  if(available<=0) return 'out';
  if(available<=60) return 'low';
  if(limitSeconds){
    const fraction=available/limitSeconds;
    if(fraction<=0.2) return 'low';
    if(fraction<=0.5) return 'warn';
  }
  return 'ok';
}
function usageCategory(id){
  return usageStatus&&Array.isArray(usageStatus.categories)?usageStatus.categories.find(c=>c.id===id):null;
}
// Categorias que dividem o mesmo limite (ex.: Jogos + Passatempo) viram um grupo.
function usageGroups(){
  const groups=[], byPool={};
  for(const c of (usageStatus&&usageStatus.categories)||[]){
    const pool=c.pool||c.id;
    let g=byPool[pool];
    if(!g){ g=byPool[pool]={pool,members:[],minutes:c.minutes,used:0,available:c.availableSeconds,exhausted:c.exhausted}; groups.push(g); }
    g.members.push(c);
    g.used=c.poolUsedSeconds!==undefined?c.poolUsedSeconds:g.used+(c.usedSeconds||0);
  }
  for(const g of groups){
    g.label=g.members.map(c=>c.label).join(' + ');
    g.emoji=g.members.map(c=>c.emoji).join('');
  }
  return groups;
}
function usageAlternativesText(excludeId){
  if(!usageStatus||usageStatus.totalExhausted) return '';
  const own=usageCategory(excludeId), ownPool=own?(own.pool||own.id):excludeId;
  const options=(usageStatus.categories||[]).filter(c=>c.id!==excludeId&&(c.pool||c.id)!==ownPool&&!c.exhausted&&(c.availableSeconds===null||c.availableSeconds>0));
  if(!options.length) return '';
  return 'Você ainda pode brincar de '+options.map(c=>c.label+' '+c.emoji+(c.availableSeconds!==null?' ('+usageMinutes(c.availableSeconds)+' min)':'')).join(' ou ')+'.';
}

// ---------- Regra de aprendizado (ontem Aprender < meta → hoje Jogar menor) ----------
function usageLearningRule(){
  const r=usageStatus&&usageStatus.enabled&&usageStatus.learningRule;
  return r&&r.enabled?r:null;
}
// Regra valendo hoje para esta categoria (Jogos e quem divide o pool, ex.: Passatempo)
function usageLearningReducedFor(categoryId){
  const r=usageLearningRule(), cat=usageCategory(categoryId);
  return r&&r.active&&cat&&cat.learningReduced?r:null;
}
function usageLearningKidText(r){ return 'Hoje '+r.minutes+' min — ontem faltou aprender 📚'; }
// Dica no cartão Aprender: quanto falta hoje para Jogar ficar inteiro amanhã
function usageLearningGoalKidText(){
  const r=usageLearningRule();
  const t=r&&r.today;
  if(!t||t.goalSeconds===null||t.goalSeconds===undefined||t.goalSeconds<=0) return '';
  if(t.met) return 'Meta de hoje cumprida! ⭐';
  return 'Aprenda '+usageMinutes(t.goalSeconds-t.learnedSeconds)+' min e amanhã tem Jogar inteiro ⭐';
}
function usageLearningParentText(){
  const r=usageLearningRule();
  if(!r) return '';
  const learned=usageUsedMinutes(r.yesterdayLearnedSeconds);
  const goalMin=r.goalSeconds===null||r.goalSeconds===undefined?null:Math.round(r.goalSeconds/60);
  const learnText='ontem 📚 Aprender foi '+learned+(r.yesterdayLearningMinutes!==null&&r.yesterdayLearningMinutes!==undefined?'/'+r.yesterdayLearningMinutes:'')+' min'+(goalMin!==null?' (meta '+goalMin+' min)':'');
  let text;
  if(r.reason==='goal_missed'&&r.active) text='Hoje: 🎮 Jogar reduzido para '+r.minutes+' min (de '+r.baseMinutes+') porque '+learnText+'.';
  else if(r.reason==='goal_missed') text='Hoje sem redução: a meta não foi cumprida, mas a redução configurada é de 100%.';
  else if(r.reason==='goal_met') text='Hoje sem redução: '+learnText+' ✔';
  else if(r.reason==='no_usage') text='Hoje sem redução: ontem este perfil não usou o notebook.';
  else if(r.reason==='no_goal') text='Hoje sem redução: 📚 Aprender estava sem limite ontem, então não havia meta.';
  else if(r.reason==='no_play_limit') text='Hoje sem redução: 🎮 Jogar está sem limite hoje.';
  else text='Hoje sem redução.';
  const t=r.today||{};
  if(t.goalSeconds!==null&&t.goalSeconds!==undefined&&t.goalSeconds>0){
    text+=' Para amanhã: '+usageUsedMinutes(t.learnedSeconds)+'/'+Math.round(t.goalSeconds/60)+' min de Aprender'+(t.met?' ✔':'')+'.';
  }
  return text;
}

// ---------- Medidores na tela da criança ----------
function renderUsageMeters(){
  const host=document.getElementById('usageMeters');
  if(!host) return;
  host.replaceChildren();
  if(!usageStatus||!usageStatus.enabled){ host.hidden=true; return; }
  const items=[];
  const groups=usageGroups();
  for(const g of groups){
    if(g.minutes===null||g.minutes===undefined) continue;
    const reduced=g.members.some(c=>usageLearningReducedFor(c.id));
    items.push({emoji:g.emoji,label:g.label,used:g.used,limit:g.minutes*60,available:g.available,exhausted:g.exhausted,
      note:reduced?'ontem faltou aprender 📚':'',noteLong:reduced?usageLearningKidText(usageLearningRule()):''});
  }
  const sum=groups.reduce((acc,g)=>acc+(g.minutes===null||g.minutes===undefined?Infinity:g.minutes),0);
  if(usageStatus.totalMinutes!==null&&usageStatus.totalMinutes!==undefined&&(usageStatus.totalMinutes<sum||!items.length)){
    items.push({emoji:'⏳',label:'Hoje',used:usageStatus.totalUsedSeconds,limit:usageStatus.totalMinutes*60,available:usageStatus.totalRemainingSeconds,exhausted:usageStatus.totalExhausted});
  }
  if(!items.length){ host.hidden=true; return; }
  for(const item of items){
    const band=item.exhausted?'out':usageBand(item.available,item.limit);
    const pill=document.createElement('div');
    pill.className='smallbtn usage-pill usage-'+band;
    const usedMin=Math.min(usageUsedMinutes(item.used),item.limit/60);
    const limitMin=Math.round(item.limit/60);
    pill.setAttribute('role','img');
    pill.setAttribute('aria-label',item.label+': '+usedMin+' de '+limitMin+' minutos usados'+(item.noteLong?'. '+item.noteLong:''));
    if(item.noteLong) pill.title=item.noteLong;
    const emoji=document.createElement('span');
    emoji.className='usage-emoji';
    emoji.textContent=item.exhausted?'🔒':item.emoji;
    const text=document.createElement('span');
    text.className='usage-text';
    const name=document.createElement('span');
    name.className='usage-name';
    name.textContent=item.label;
    const bar=document.createElement('span');
    bar.className='usage-bar';
    const fill=document.createElement('span');
    fill.className='usage-fill';
    const fraction=item.limit>0?Math.min(1,(item.used||0)/item.limit):1;
    fill.style.width=Math.round((item.exhausted?1:fraction)*100)+'%';
    bar.appendChild(fill);
    text.append(name,bar);
    if(item.note){
      const note=document.createElement('span');
      note.className='usage-note';
      note.textContent=item.note;
      text.appendChild(note);
    }
    const count=document.createElement('span');
    count.className='usage-count';
    count.textContent=item.exhausted?'acabou':usedMin+'/'+limitMin+' min';
    pill.append(emoji,text,count);
    host.appendChild(pill);
  }
  host.hidden=false;
}

async function pollUsage(){
  try{
    const response=await fetch('/api/usage/status',{cache:'no-store'});
    if(!response.ok) return;
    const data=await response.json();
    if(!data||typeof data!=='object') return;
    const before=usageStatus?(usageStatus.blockedTileIds||[]).join('\n'):'';
    usageStatus=data;
    renderUsageMeters();
    if(typeof escolhaOnUsage==='function') escolhaOnUsage();
    if((data.blockedTileIds||[]).join('\n')!==before&&typeof pollAvailability==='function') pollAvailability();
    maybeShowUsageExpiry();
    if(!document.getElementById('admin').classList.contains('hidden')) renderUsageLimitSettingsStatus();
  }catch(e){}
}
function startUsagePolling(){
  pollUsage();
  if(usagePollInterval===null) usagePollInterval=setInterval(pollUsage,5000);
}
document.addEventListener('visibilitychange',()=>{ if(!document.hidden) pollUsage(); });
window.addEventListener('focus',()=>pollUsage());

// ---------- Mensagem amigável ----------
function showUsageMessage(title,body){
  const overlay=document.getElementById('usageMessage');
  if(!overlay) return;
  document.getElementById('usageMessageTitle').textContent=title;
  document.getElementById('usageMessageBody').textContent=body;
  overlay.classList.remove('hidden');
  document.getElementById('usageMessageOk').focus();
  if(usageMessageTimer!==null) clearTimeout(usageMessageTimer);
  usageMessageTimer=setTimeout(hideUsageMessage,15000);
}
function hideUsageMessage(){
  const overlay=document.getElementById('usageMessage');
  if(overlay) overlay.classList.add('hidden');
  if(usageMessageTimer!==null) clearTimeout(usageMessageTimer);
  usageMessageTimer=null;
}
function usageLimitTexts(reason,categoryId){
  const cat=usageCategory(categoryId);
  if(reason==='daily_limit'||(usageStatus&&usageStatus.totalExhausted)||!cat){
    return ['O tempo de hoje acabou!','Que tal brincar longe da tela? Amanhã tem mais! 😊'];
  }
  const other=usageAlternativesText(categoryId);
  // Regra de aprendizado ligada: lembrete positivo de que Aprender hoje dá mais Jogar amanhã
  const r=usageLearningRule();
  const learnTip=r&&cat.pool===r.category&&r.today&&!r.today.met&&r.today.goalSeconds>0
    ? ' Aprendendo um pouquinho hoje, amanhã tem mais tempo de jogar! 📚' : '';
  return ['O tempo de '+cat.label+' acabou por hoje!', (other||'Amanhã tem mais! 😊')+learnTip];
}
function maybeShowUsageExpiry(){
  const expiry=usageStatus&&usageStatus.lastExpiry;
  if(!expiry||!expiry.at||expiry.at<=usageLastExpiryShown) return;
  const now=usageStatus.now||Math.floor(Date.now()/1000);
  if(now-expiry.at>180) return;
  usageLastExpiryShown=expiry.at;
  try{ sessionStorage.setItem('cozyUsageExpiryShown',String(expiry.at)); }catch(e){}
  if(!document.getElementById('admin').classList.contains('hidden')) return;
  const [title,body]=usageLimitTexts(expiry.limitedBy==='total'?'daily_limit':'category_limit',expiry.category);
  showUsageMessage(title,body);
}
function usageLimitReason(tileId){
  const reasons=(availabilityStatus&&availabilityStatus.limitBlocked)||(usageStatus&&usageStatus.blockedReasons)||{};
  return reasons[tileId]||'';
}
function tileCategoryId(tileId){
  const tile=cfg&&cfg.tiles?cfg.tiles.find(t=>t.id===tileId):null;
  return tile?(tile.category||''):'';
}
function showUsageLimitBlock(reason,tileId){
  const [title,body]=usageLimitTexts(reason,tileCategoryId(tileId));
  showUsageMessage(title,body);
}

// ---------- Painel dos pais (Screen Time) ----------
const USAGE_DEFAULT_CATEGORIES={jogos:{label:'Jogos',emoji:'🎮'},educativo:{label:'Aprender',emoji:'📚'},passatempo:{label:'Passatempo',emoji:'🎨'}};
function ensureCategoryLimits(){
  if(!cfg.categoryLimits||typeof cfg.categoryLimits!=='object'){
    cfg.categoryLimits={enabled:false,totalMinutes:60,categories:{jogos:{minutes:30},educativo:{minutes:30},passatempo:{minutes:null,pool:'jogos'}}};
  }
  if(!cfg.categoryLimits.categories||typeof cfg.categoryLimits.categories!=='object') cfg.categoryLimits.categories={};
  return cfg.categoryLimits;
}
function categoryDisplay(id){
  const entry=(cfg.categoryLimits&&cfg.categoryLimits.categories||{})[id]||{};
  const builtin=USAGE_DEFAULT_CATEGORIES[id]||{};
  return {label:entry.label||builtin.label||id,emoji:entry.emoji||builtin.emoji||'⭐'};
}
function parseLimitInput(input){
  const raw=input.value.trim();
  if(raw==='') return null;
  const value=parseInt(raw,10);
  return Number.isFinite(value)?Math.max(0,Math.min(1440,value)):null;
}
function minutesInput(value,label,onchange){
  const input=document.createElement('input');
  input.type='number'; input.min='0'; input.max='1440'; input.step='5';
  input.placeholder='sem limite';
  input.value=value===null||value===undefined?'':String(value);
  input.setAttribute('aria-label',label);
  input.onchange=()=>onchange(parseLimitInput(input));
  return input;
}
const USAGE_WEEKDAYS=[
  {id:'mon',label:'Seg'},{id:'tue',label:'Ter'},{id:'wed',label:'Qua'},{id:'thu',label:'Qui'},
  {id:'fri',label:'Sex'},{id:'sat',label:'Sáb'},{id:'sun',label:'Dom'},
];
function usageTodayWeekday(){ return ['sun','mon','tue','wed','thu','fri','sat'][new Date().getDay()]; }
function usageDayFromDefault(limits){
  const categories={};
  for(const id of Object.keys(limits.categories)) categories[id]=limits.categories[id].minutes??null;
  return {totalMinutes:limits.totalMinutes??null,categories};
}
function usageWeekdayTable(limits){
  const wrap=document.createElement('div');
  wrap.className='usage-weekday-wrap';
  const table=document.createElement('table');
  table.className='usage-weekday-table';
  const today=usageTodayWeekday();
  const head=table.createTHead().insertRow();
  head.appendChild(document.createElement('th'));
  for(const day of USAGE_WEEKDAYS){
    const th=document.createElement('th');
    th.textContent=day.label+(day.id===today?' (hoje)':'');
    if(day.id===today) th.className='usage-today-col';
    if(day.id==='sat'||day.id==='sun') th.classList.add('usage-weekend-col');
    head.appendChild(th);
  }
  const body=table.createTBody();
  const rows=[{id:'',label:'⏳ Total do dia'}].concat(Object.keys(limits.categories).filter(id=>!usagePooled(limits,id)).map(id=>{
    const d=categoryDisplay(id); return {id,label:d.emoji+' '+d.label};
  }));
  for(const rowDef of rows){
    const row=body.insertRow();
    const th=document.createElement('th'); th.scope='row'; th.textContent=rowDef.label; row.appendChild(th);
    for(const day of USAGE_WEEKDAYS){
      const entry=limits.weekdays[day.id]||(limits.weekdays[day.id]=usageDayFromDefault(limits));
      if(!entry.categories) entry.categories={};
      const value=rowDef.id===''
        ? ('totalMinutes' in entry?entry.totalMinutes:limits.totalMinutes)
        : (rowDef.id in entry.categories?entry.categories[rowDef.id]:limits.categories[rowDef.id].minutes);
      const cell=row.insertCell();
      if(day.id===today) cell.className='usage-today-col';
      cell.appendChild(minutesInput(value,rowDef.label+' — '+day.label,v=>{
        if(rowDef.id==='') entry.totalMinutes=v; else entry.categories[rowDef.id]=v;
      }));
    }
  }
  wrap.appendChild(table);
  // Atalho: copiar a segunda para os outros dias úteis
  const copy=document.createElement('button');
  copy.type='button'; copy.className='smallbtn';
  copy.textContent='Copiar Seg para Ter–Sex';
  copy.onclick=()=>{
    for(const id of ['tue','wed','thu','fri']) limits.weekdays[id]=JSON.parse(JSON.stringify(limits.weekdays.mon));
    renderUsageLimitSettings();
  };
  wrap.appendChild(copy);
  return wrap;
}
function usagePooled(limits,id){
  const pool=(limits.categories[id]||{}).pool;
  return !!pool&&pool!==id&&!!limits.categories[pool];
}
function renderUsageLimitSettings(){
  const panel=document.getElementById('usageLimitSettings');
  if(!panel||!cfg) return;
  const limits=ensureCategoryLimits();
  const enabled=document.getElementById('usageLimitsEnabled');
  enabled.checked=!!limits.enabled;
  enabled.onchange=()=>{ limits.enabled=enabled.checked; renderUsageLimitSettings(); };
  const fields=document.getElementById('usageLimitFields');
  fields.hidden=!limits.enabled;
  fields.replaceChildren();
  const addRow=(labelText,input)=>{
    const row=document.createElement('label');
    row.className='usage-limit-row';
    const span=document.createElement('span');
    span.textContent=labelText;
    const unit=document.createElement('span');
    unit.className='muted'; unit.textContent='min por dia';
    row.append(span,input,unit);
    fields.appendChild(row);
  };
  const byDay=!!(limits.weekdays&&Object.keys(limits.weekdays).length);
  if(!byDay){
    addRow('⏳ Total do dia',minutesInput(limits.totalMinutes,'Total do dia em minutos',v=>{ limits.totalMinutes=v; }));
    for(const id of Object.keys(limits.categories)){
      const d=categoryDisplay(id);
      if(usagePooled(limits,id)) continue;
      addRow(d.emoji+' '+d.label,minutesInput(limits.categories[id].minutes,d.label+' em minutos',v=>{ limits.categories[id].minutes=v; }));
    }
  }
  // Categorias que podem dividir o tempo dos Jogos (ex.: Passatempo)
  for(const id of Object.keys(limits.categories)){
    if(id==='jogos'||!limits.categories.jogos) continue;
    if(id!=='passatempo'&&!limits.categories[id].pool) continue;
    const d=categoryDisplay(id), j=categoryDisplay('jogos');
    const share=document.createElement('label');
    share.className='chk usage-pool-toggle';
    const check=document.createElement('input');
    check.type='checkbox'; check.checked=usagePooled(limits,id);
    check.onchange=()=>{
      if(check.checked){ limits.categories[id].pool='jogos'; limits.categories[id].minutes=null; }
      else{ delete limits.categories[id].pool; limits.categories[id].minutes=limits.categories.jogos.minutes??30; }
      renderUsageLimitSettings();
    };
    share.append(check,document.createTextNode(' '+d.emoji+' '+d.label+' divide o tempo com '+j.emoji+' '+j.label));
    fields.appendChild(share);
  }
  // Dias da semana
  const dayToggle=document.createElement('label');
  dayToggle.className='chk usage-weekday-toggle';
  const dayCheck=document.createElement('input');
  dayCheck.type='checkbox'; dayCheck.checked=byDay;
  dayCheck.onchange=()=>{
    if(dayCheck.checked){
      limits.weekdays={};
      for(const day of USAGE_WEEKDAYS) limits.weekdays[day.id]=usageDayFromDefault(limits);
    }else{
      // volta ao modo "todo dia igual" usando os valores de segunda
      const mon=(limits.weekdays||{}).mon;
      if(mon){
        if('totalMinutes' in mon) limits.totalMinutes=mon.totalMinutes;
        for(const [id,min] of Object.entries(mon.categories||{})) if(limits.categories[id]) limits.categories[id].minutes=min;
      }
      delete limits.weekdays;
    }
    renderUsageLimitSettings();
  };
  dayToggle.append(dayCheck,document.createTextNode(' 📅 Tempo diferente em cada dia da semana'));
  fields.appendChild(dayToggle);
  if(byDay) fields.appendChild(usageWeekdayTable(limits));
  fields.appendChild(learningRuleSettings(limits));
  const hint=document.createElement('p');
  hint.className='muted';
  hint.textContent='O tempo só conta enquanto um app ou site da categoria está aberto e zera à meia-noite. Campo vazio = sem limite. Clique em Salvar para aplicar.'+(byDay?' Cada dia usa a sua coluna.':'');
  fields.appendChild(hint);

  // Categoria de cada tile
  const list=document.getElementById('usageTileCategories');
  list.replaceChildren();
  const categoryIds=Object.keys(limits.categories);
  for(const tile of cfg.tiles){
    const row=document.createElement('label');
    row.className='usage-tile-row'+(tile.visible?'':' usage-tile-hidden');
    const name=document.createElement('span');
    name.textContent=(tile.label||tile.id)+(tile.visible?'':' (oculto)');
    const select=document.createElement('select');
    select.setAttribute('aria-label','Categoria de '+(tile.label||tile.id));
    for(const id of categoryIds){
      const d=categoryDisplay(id);
      const opt=document.createElement('option');
      opt.value=id; opt.textContent=d.emoji+' '+d.label;
      select.appendChild(opt);
    }
    const none=document.createElement('option');
    none.value=''; none.textContent='— Sem categoria (só o total)';
    select.appendChild(none);
    const current=tile.category||'';
    if(current&&!categoryIds.includes(current)){
      const opt=document.createElement('option');
      opt.value=current; opt.textContent=current;
      select.appendChild(opt);
    }
    select.value=current;
    select.onchange=()=>{ tile.category=select.value; };
    row.append(name,select);
    list.appendChild(row);
  }
  document.getElementById('usageTileCategoriesWrap').hidden=!limits.enabled;
  renderUsageLimitSettingsStatus();
}
// Regra de aprendizado: meta de Aprender e quanto sobra de Jogar no dia seguinte
const LEARNING_RULE_DEFAULTS={enabled:false,goalPercent:50,reducedPercent:50,mode:'fixed'};
function percentInput(value,min,label,onchange){
  const input=document.createElement('input');
  input.type='number'; input.min=String(min); input.max='100'; input.step='5';
  input.value=String(value);
  input.setAttribute('aria-label',label);
  input.onchange=()=>{
    const parsed=parseInt(input.value,10);
    const clean=Number.isFinite(parsed)?Math.max(min,Math.min(100,parsed)):value;
    input.value=String(clean);
    onchange(clean);
  };
  return input;
}
function learningRuleSettings(limits){
  const rule=Object.assign({},LEARNING_RULE_DEFAULTS,limits.learningRule||{});
  const box=document.createElement('div');
  box.className='usage-learning-rule';
  const toggle=document.createElement('label');
  toggle.className='chk usage-learning-toggle';
  const check=document.createElement('input');
  check.type='checkbox'; check.checked=!!rule.enabled;
  check.onchange=()=>{ limits.learningRule=Object.assign(rule,{enabled:check.checked}); renderUsageLimitSettings(); };
  toggle.append(check,document.createTextNode(' 📚 Regra de aprendizado: se não aprender, 🎮 Jogar no dia seguinte fica menor'));
  box.appendChild(toggle);
  if(!rule.enabled) return box;
  limits.learningRule=rule;
  const row=(labelText,input,unitText)=>{
    const el=document.createElement('label');
    el.className='usage-limit-row usage-learning-row';
    const span=document.createElement('span'); span.textContent=labelText;
    const unit=document.createElement('span'); unit.className='muted'; unit.textContent=unitText;
    el.append(span,input,unit);
    box.appendChild(el);
  };
  const example=document.createElement('p');
  example.className='muted';
  const updateExample=()=>{
    const learn=(limits.categories.educativo||{}).minutes, play=(limits.categories.jogos||{}).minutes;
    if(learn===null||learn===undefined||play===null||play===undefined){
      example.textContent='A regra precisa de limite em 📚 Aprender (para ter meta) e em 🎮 Jogos (para reduzir).';
      return;
    }
    const goal=Math.floor(learn*rule.goalPercent/100), reduced=Math.floor(play*rule.reducedPercent/100);
    example.textContent='Ex.: com Aprender '+learn+' min e Jogar '+play+' min, a meta é '+goal+' min de Aprender. '
      +'Se ontem ficou abaixo disso, hoje Jogar fica com '+(rule.mode==='proportional'?'entre '+reduced+' e '+play:reduced)+' min. '
      +'Dias em que o notebook não foi usado não contam. Quem divide o tempo do Jogar (ex.: 🎨 Passatempo) também diminui; o total do dia e o Aprender não mudam. '
      +'Com tempo diferente em cada dia da semana, vale a coluna de ontem (meta) e a de hoje (Jogar).';
  };
  row('Meta de Aprender',percentInput(rule.goalPercent,1,'Meta de Aprender em % do tempo de Aprender',v=>{ rule.goalPercent=v; updateExample(); }),'% do tempo de Aprender');
  row('Se não cumprir, Jogar no dia seguinte fica com',percentInput(rule.reducedPercent,0,'Jogar no dia seguinte em %',v=>{ rule.reducedPercent=v; updateExample(); }),'% do tempo de Jogar');
  const prop=document.createElement('label');
  prop.className='chk usage-learning-toggle';
  const propCheck=document.createElement('input');
  propCheck.type='checkbox'; propCheck.checked=rule.mode==='proportional';
  propCheck.onchange=()=>{ rule.mode=propCheck.checked?'proportional':'fixed'; updateExample(); };
  prop.append(propCheck,document.createTextNode(' Proporcional: quem aprendeu um pouco perde menos tempo de Jogar'));
  box.appendChild(prop);
  updateExample();
  box.appendChild(example);
  const status=document.createElement('p');
  status.id='learningRuleStatus';
  status.className='usage-learning-status';
  status.setAttribute('aria-live','polite');
  box.appendChild(status);
  return box;
}
function renderLearningRuleStatus(){
  const target=document.getElementById('learningRuleStatus');
  if(!target) return;
  const saved=usageStatus&&usageStatus.learningRule&&usageStatus.learningRule.enabled;
  target.textContent=saved?usageLearningParentText():'Clique em Salvar para ativar a regra neste perfil.';
}
function renderUsageLimitSettingsStatus(){
  renderLearningRuleStatus();
  const target=document.getElementById('usageTodayStatus');
  if(!target) return;
  if(!usageStatus||!usageStatus.enabled){ target.textContent='Limites desativados (ou ainda não salvos) para este perfil.'; return; }
  const parts=usageGroups().map(g=>g.emoji+' '+g.label+': '+usageUsedMinutes(g.used)+(g.minutes!==null&&g.minutes!==undefined?'/'+g.minutes:'')+' min');
  parts.push('⏳ Total: '+usageUsedMinutes(usageStatus.totalUsedSeconds)+(usageStatus.totalMinutes!==null&&usageStatus.totalMinutes!==undefined?'/'+usageStatus.totalMinutes:'')+' min');
  target.textContent='Hoje: '+parts.join(' · ');
}
async function resetUsageToday(){
  if(!cfg) return;
  const ok=typeof requestConfirmation==='function'
    ? await requestConfirmation('Zerar o tempo usado hoje por '+(cfg.name||'este perfil')+'?','Zerar')
    : true;
  if(!ok) return;
  try{
    await fetch('/api/usage/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profileId:cfg.activeProfileId||'default'})});
  }catch(e){}
  await pollUsage();
  if(typeof pollAvailability==='function') await pollAvailability();
  renderUsageLimitSettingsStatus();
}

document.addEventListener('DOMContentLoaded',()=>{
  const ok=document.getElementById('usageMessageOk');
  if(ok) ok.onclick=hideUsageMessage;
  startUsagePolling();
});
