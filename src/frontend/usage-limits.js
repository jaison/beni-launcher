// Limites diários por categoria (Jogos / Aprender): medidores para a criança,
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
function usageAlternativesText(excludeId){
  if(!usageStatus||usageStatus.totalExhausted) return '';
  const options=(usageStatus.categories||[]).filter(c=>c.id!==excludeId&&!c.exhausted&&(c.availableSeconds===null||c.availableSeconds>0));
  if(!options.length) return '';
  return 'Você ainda pode brincar de '+options.map(c=>c.label+' '+c.emoji+(c.availableSeconds!==null?' ('+usageMinutes(c.availableSeconds)+' min)':'')).join(' ou ')+'.';
}

// ---------- Medidores na tela da criança ----------
function renderUsageMeters(){
  const host=document.getElementById('usageMeters');
  if(!host) return;
  host.replaceChildren();
  if(!usageStatus||!usageStatus.enabled){ host.hidden=true; return; }
  const items=[];
  for(const c of usageStatus.categories||[]){
    if(c.minutes===null||c.minutes===undefined) continue;
    items.push({emoji:c.emoji,label:c.label,used:c.usedSeconds,limit:c.minutes*60,available:c.availableSeconds,exhausted:c.exhausted});
  }
  const sum=(usageStatus.categories||[]).reduce((acc,c)=>acc+(c.minutes===null||c.minutes===undefined?Infinity:c.minutes),0);
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
    pill.setAttribute('aria-label',item.label+': '+usedMin+' de '+limitMin+' minutos usados');
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
  return ['O tempo de '+cat.label+' acabou por hoje!', other||'Amanhã tem mais! 😊'];
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
const USAGE_DEFAULT_CATEGORIES={jogos:{label:'Jogos',emoji:'🎮'},educativo:{label:'Aprender',emoji:'📚'}};
function ensureCategoryLimits(){
  if(!cfg.categoryLimits||typeof cfg.categoryLimits!=='object'){
    cfg.categoryLimits={enabled:false,totalMinutes:60,categories:{jogos:{minutes:30},educativo:{minutes:30}}};
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
  addRow('⏳ Total do dia',minutesInput(limits.totalMinutes,'Total do dia em minutos',v=>{ limits.totalMinutes=v; }));
  for(const id of Object.keys(limits.categories)){
    const d=categoryDisplay(id);
    addRow(d.emoji+' '+d.label,minutesInput(limits.categories[id].minutes,d.label+' em minutos',v=>{ limits.categories[id].minutes=v; }));
  }
  const hint=document.createElement('p');
  hint.className='muted';
  hint.textContent='O tempo só conta enquanto um app ou site da categoria está aberto e zera à meia-noite. Campo vazio = sem limite. Clique em Salvar para aplicar.';
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
function renderUsageLimitSettingsStatus(){
  const target=document.getElementById('usageTodayStatus');
  if(!target) return;
  if(!usageStatus||!usageStatus.enabled){ target.textContent='Limites desativados (ou ainda não salvos) para este perfil.'; return; }
  const parts=(usageStatus.categories||[]).map(c=>c.emoji+' '+c.label+': '+usageUsedMinutes(c.usedSeconds)+(c.minutes!==null&&c.minutes!==undefined?'/'+c.minutes:'')+' min');
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
