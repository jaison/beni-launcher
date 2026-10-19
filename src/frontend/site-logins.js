// Pais → Crianças: e-mail e senha dos sites (Khan Academy) por perfil, para o
// login automático. A senha só vai para o servidor; ele nunca a devolve.
async function loadSiteLogins(){
  const list=document.getElementById('siteLoginList');
  if(!list) return;
  const who=document.getElementById('siteLoginProfile');
  if(who) who.textContent=(cfg&&cfg.name)||'esta criança';
  try{
    const response=await fetch('/api/site-logins',{cache:'no-store'});
    if(!response.ok) throw new Error(String(response.status));
    renderSiteLogins((await response.json()).sites||[]);
  }catch(e){
    list.replaceChildren();
    siteLoginMessage('Não consegui carregar os logins salvos.',true);
  }
}
function siteLoginMessage(text,error){
  const box=document.getElementById('siteLoginMessage');
  if(!box) return;
  box.hidden=!text;
  box.textContent=text||'';
  box.className='ui-state '+(error?'ui-state-error':'ui-state-success');
}
async function siteLoginSend(body){
  try{
    const response=await fetch('/api/site-logins',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
    });
    const data=await response.json().catch(()=>({}));
    if(!response.ok) throw new Error(data.message||String(response.status));
    renderSiteLogins(data.sites||[]);
    return true;
  }catch(e){
    const msg=String(e.message||'');
    siteLoginMessage(msg.includes('password')?'Digite a senha.':msg.includes('username')?'Digite o e-mail ou nome de usuário.':'Não consegui salvar ('+msg+').',true);
    return false;
  }
}
function renderSiteLogins(sites){
  const list=document.getElementById('siteLoginList');
  if(!list) return;
  list.replaceChildren();
  for(const site of sites){
    const row=document.createElement('div');
    row.className='site-login-row';
    const name=document.createElement('span');
    name.className='site-login-name';
    name.textContent=site.label;
    const user=document.createElement('input');
    user.type='text'; user.autocomplete='off'; user.spellcheck=false;
    user.placeholder='E-mail ou nome de usuário';
    user.value=site.username||'';
    user.setAttribute('aria-label',site.label+': e-mail ou nome de usuário');
    const pass=document.createElement('input');
    pass.type='password'; pass.autocomplete='new-password';
    pass.placeholder=site.hasPassword?'senha salva (digite para trocar)':'Senha';
    pass.setAttribute('aria-label',site.label+': senha');
    const save=document.createElement('button');
    save.type='button'; save.className='smallbtn';
    save.textContent='Salvar login';
    save.onclick=async()=>{
      if(await siteLoginSend({site:site.id,username:user.value,password:pass.value})){
        siteLoginMessage('Login do '+site.label+' salvo. Na próxima vez que '+((cfg&&cfg.name)||'a criança')+' abrir o site, ele entra sozinho.');
      }
    };
    row.append(name,user,pass,save);
    if(site.hasPassword){
      const remove=document.createElement('button');
      remove.type='button'; remove.className='smallbtn';
      remove.textContent='Remover';
      remove.onclick=async()=>{
        const ok=typeof requestConfirmation==='function'
          ? await requestConfirmation('Remover o login do '+site.label+' de '+((cfg&&cfg.name)||'este perfil')+'?','Remover')
          : true;
        if(ok&&await siteLoginSend({site:site.id,remove:true})) siteLoginMessage('Login removido.');
      };
      row.appendChild(remove);
      const saved=document.createElement('span');
      saved.className='muted site-login-saved';
      saved.textContent='✔ Login automático ligado para '+(site.username||'');
      row.appendChild(saved);
    }
    list.appendChild(row);
  }
}
