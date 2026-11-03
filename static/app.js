const $ = id => document.getElementById(id);
const set = (id, value) => $(id).textContent = value;
const setBar = (id, value) => $(id).style.width = `${Math.min(100, value)}%`;

function render(s) {
  set('host', s.host); set('os', `${s.os} · ${s.kernel} · ${s.architecture}`); set('cpu', `${s.cpu}%`); setBar('cpu-bar', s.cpu);
  set('cores', `${s.physical_cores} cores / ${s.cores} threads · load ${s.load.join(', ')}`);
  set('memory', `${s.memory.percent}%`); setBar('memory-bar', s.memory.percent); set('memory-detail', `${s.memory.used} / ${s.memory.total}`);
  set('disk', `${s.disk.percent}%`); setBar('disk-bar', s.disk.percent); set('disk-detail', `${s.disk.used} / ${s.disk.total}`);
  set('uptime', s.uptime); set('python', s.python); set('ram-detail', `${s.memory.used} / ${s.memory.total}`); set('swap-detail', `${s.swap.used} / ${s.swap.total} (${s.swap.percent}%)`); set('disk-overview', `${s.disk.used} / ${s.disk.total} (${s.disk.percent}%)`); const bot = $('bot'); bot.textContent = s.bot_online ? 'Running' : 'Offline'; bot.className = s.bot_online ? 'good' : 'bad';
  set('battery', s.battery.available ? `${s.battery.percent}% · ${s.battery.charging ? 'Charging' : 'On battery'}` : 'Not detected');
  set('battery-remaining', s.battery.available ? s.battery.remaining : '—');
  $('temperatures').innerHTML = s.temperatures.length ? s.temperatures.map(t => `<div class="temperature"><span>${t.device}</span><b>${t.current.toFixed(1)}°C</b><small>${t.label}</small></div>`).join('') : '<p class="empty-state">No readable temperature sensors found.</p>';
  set('updated', `Live · ${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})}`);
}

const stream = new EventSource('/api/events');
stream.onmessage = event => render(JSON.parse(event.data));
stream.onerror = () => set('updated', 'Reconnecting to live status…');

let pendingAction;
const dialog = $('confirm-dialog');
document.querySelectorAll('[data-action]').forEach(button => button.onclick = () => {
  pendingAction = button.dataset.action; const reboot = pendingAction === 'reboot';
  set('modal-title', reboot ? 'Restart laptop?' : 'Shut down laptop?');
  set('modal-copy', `Type ${pendingAction} to confirm this action.`); $('confirmation').value = ''; $('confirmation').placeholder = pendingAction; dialog.showModal();
});
$('confirm-button').onclick = async event => {
  event.preventDefault(); if ($('confirmation').value !== pendingAction) { $('confirmation').focus(); return; }
  $('confirm-button').disabled = true;
  const r = await fetch(`/api/power/${pendingAction}`, {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':window.CSRF_TOKEN}, body:JSON.stringify({confirm:pendingAction})});
  $('confirm-button').disabled = false; if (r.ok) { dialog.close(); set('updated', `Command sent: ${pendingAction}`); } else { set('modal-copy', 'Could not send action. Check server permissions.'); }
};
$('logout').onclick = async () => { await fetch('/logout', {method:'POST', headers:{'X-CSRF-Token':window.CSRF_TOKEN}}); location.href='/login'; };

