(() => {
  const CODE_KEY = 'escolhaOM:code';
  let accessCode = (localStorage.getItem(CODE_KEY) || '').trim().toUpperCase();
  let state = null;
  let pendingUnit = null;
  let pollTimer = null;
  let busy = false;
  const qs = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  function toast(msg){ const t=qs('toast'); t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2500); }
  function setBusy(v){ busy=v; qs('app').classList.toggle('loading',v); }
  async function api(url, opts={}){
    const r=await fetch(url,{cache:'no-store',headers:{'Content-Type':'application/json',...(opts.headers||{})},...opts});
    let data={}; try{data=await r.json()}catch(_){ }
    if(!r.ok) throw new Error(data.detail || `Erro HTTP ${r.status}`);
    return data;
  }
  async function loadState(silent=false){
    if(!silent)setBusy(true);
    try{
      state=await api(`/api/state${accessCode?`?code=${encodeURIComponent(accessCode)}`:''}`);
      render(); qs('connText').textContent='Sincronizado'; qs('connDot').className='dot ok';
    }catch(e){ qs('connText').textContent='Falha de conexão'; qs('connDot').className='dot off'; if(!silent)toast(e.message); }
    finally{if(!silent)setBusy(false)}
  }
  function currentQueue(offset=0){
    if(!state?.event)return null;
    const pos=Number(state.event.current_position)+offset;
    return (state.queue||[]).find(x=>Number(x.position)===pos)||null;
  }
  function render(){
    if(!state)return;
    const e=state.event;
    qs('eventTitle').textContent=e.title; qs('eventCourse').textContent=e.course;
    qs('eventStatus').textContent=e.is_open?'Escolhas abertas':'Escolhas fechadas'; qs('eventDot').className='dot '+(e.is_open?'ok':'off');
    const total=(state.units||[]).reduce((a,u)=>a+Number(u.capacity||0),0), used=(state.choices||[]).length;
    qs('totalVagas').textContent=total; qs('totalEscolhas').textContent=used; qs('restantes').textContent=Math.max(0,total-used); qs('posAtual').textContent=e.current_position||'—';
    qs('pista').textContent=currentQueue(0)?.name||'—'; qs('paddock').textContent=currentQueue(1)?.name||'—'; qs('aquece').textContent=currentQueue(2)?.name||'—';
    qs('upcoming').innerHTML=(state.queue||[]).filter(x=>Number(x.position)>=Number(e.current_position)+3).slice(0,12).map(x=>`<span class="chip">${x.position}º · ${esc(x.name)}</span>`).join('')||'<span class="hint">Não há mais nomes após “Aquece”.</span>';
    if(state.me){
      qs('userBadge').textContent=`${state.me.position}º · ${state.me.name}`; qs('logoutBtn').hidden=false; qs('accessBtn').textContent='Trocar código';
      const n=qs('myNotice');
      if(state.me.chosen){n.className='notice good';n.innerHTML=`<strong>${esc(state.me.name)}</strong>: sua escolha já foi registrada.`}
      else if(state.me.can_choose){n.className='notice turn';n.innerHTML=`<strong>${esc(state.me.name)}, é a sua vez.</strong> Escolha uma OM disponível abaixo.`}
      else if(!e.is_open){n.className='notice closed';n.innerHTML=`<strong>${esc(state.me.name)}</strong>: aguarde a organização abrir as escolhas.`}
      else{n.className='notice';n.innerHTML=`<strong>${esc(state.me.name)}</strong>: sua posição é ${state.me.position}º. No momento está escolhendo o ${e.current_position}º da fila.`}
    }else{
      qs('userBadge').textContent='Modo visitante'; qs('logoutBtn').hidden=true; qs('accessBtn').textContent='Meu código';
      qs('myNotice').className='notice'; qs('myNotice').innerHTML='Você está em modo visitante. Digite seu código individual para liberar sua escolha na sua vez.';
    }
    renderUnits();
  }
  function renderUnits(){
    const search=(qs('search').value||'').trim().toLowerCase(), choicesByUnit=new Map();
    for(const c of state.choices||[]){if(!choicesByUnit.has(c.unit_id))choicesByUnit.set(c.unit_id,[]);choicesByUnit.get(c.unit_id).push(c)}
    const groups={};
    for(const u of state.units||[]){
      if(search&&!`${u.region_code} ${u.unit_name} ${u.city}`.toLowerCase().includes(search))continue;
      const key=`${u.side}|${u.region_code}|${u.color}`; (groups[key] ||= []).push(u);
    }
    ['left','right'].forEach(side=>{
      const col=qs(side==='left'?'leftCol':'rightCol'); col.innerHTML='';
      Object.entries(groups).filter(([k])=>k.startsWith(side+'|')).forEach(([key,units])=>{
        const [,region,color]=key.split('|'); const cap=units.reduce((a,u)=>a+Number(u.capacity),0), used=units.reduce((a,u)=>a+Number(u.used),0);
        const sec=document.createElement('section'); sec.className='region'; sec.style.setProperty('--region',color);
        sec.innerHTML=`<div class="region-head"><div class="region-title">${esc(region)} <span style="font-weight:700">(${cap} vagas)</span></div><div class="region-count">${used}/${cap} ocupadas</div></div><div class="unit-list"></div>`;
        const list=sec.querySelector('.unit-list');
        for(const u of units){
          const full=Number(u.remaining)<=0, can=!!state.me?.can_choose && state.event.is_open && !full;
          const div=document.createElement('div'); div.className='unit '+(full?'full':'');
          const assigned=(choicesByUnit.get(u.id)||[]).map(c=>`<span class="chip">${c.position}º · ${esc(c.name)}</span>`).join('');
          div.innerHTML=`<div class="unit-name">${esc(u.unit_name)}</div><div class="city">${esc(u.city)}</div><div class="vac"><strong>${u.remaining}</strong> / ${u.capacity}</div><button class="choose" ${can?'':'disabled'}>${full?'Lotada':'Escolher'}</button>${assigned?`<div class="assigned">${assigned}</div>`:''}`;
          div.querySelector('.choose').onclick=()=>openChoice(u); list.appendChild(div);
        }
        col.appendChild(sec);
      });
    });
  }
  function openChoice(u){
    if(!state.me?.can_choose)return toast('A escolha só é liberada para quem está em pista.');
    pendingUnit=u; qs('confirmName').textContent=`${state.me.position}º · ${state.me.name}`; qs('confirmOm').textContent=`${u.unit_name} — ${u.city}`; qs('confirmDialog').showModal();
  }
  async function confirmChoice(){
    if(!pendingUnit||busy)return; setBusy(true); qs('confirmChoice').disabled=true;
    try{state=await api('/api/choose',{method:'POST',body:JSON.stringify({code:accessCode,unit_id:pendingUnit.id})});qs('confirmDialog').close();pendingUnit=null;render();toast('Escolha registrada. A fila avançou.');}
    catch(e){toast(e.message);await loadState(true)}finally{qs('confirmChoice').disabled=false;setBusy(false)}
  }
  qs('accessBtn').onclick=()=>{qs('accessCode').value=accessCode;qs('accessDialog').showModal();setTimeout(()=>qs('accessCode').focus(),50)};
  qs('cancelAccess').onclick=()=>qs('accessDialog').close();
  qs('saveAccess').onclick=async()=>{accessCode=(qs('accessCode').value||'').trim().toUpperCase();if(!accessCode)return toast('Digite o código.');localStorage.setItem(CODE_KEY,accessCode);qs('accessDialog').close();await loadState()};
  qs('logoutBtn').onclick=()=>{accessCode='';localStorage.removeItem(CODE_KEY);loadState()};
  qs('cancelChoice').onclick=()=>qs('confirmDialog').close(); qs('confirmChoice').onclick=confirmChoice;
  qs('refreshBtn').onclick=()=>loadState(); qs('search').oninput=()=>state&&renderUnits();
  qs('toggleQueue').onclick=()=>qs('queueExtra').classList.toggle('show');
  loadState(); pollTimer=setInterval(()=>loadState(true),2000);
  if('serviceWorker' in navigator)navigator.serviceWorker.register('sw.js').catch(()=>{});
})();
