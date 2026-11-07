const select=document.querySelector('#tabs');
chrome.tabs.query({}).then(tabs=>{
  for(const tab of tabs.filter(t=>/^https?:/.test(t.url))) {
    const option=document.createElement('option'); option.value=tab.id;
    option.textContent=`${tab.id} ${tab.title} ${tab.url}`;
    option.selected=tab.url===new URLSearchParams(location.search).get('url');
    select.append(option);
  }
  document.querySelector('#attach').focus();
});
document.querySelector('#attach').onclick=async()=>{
  const response=await chrome.runtime.sendMessage({attach:Number(select.value)});
  document.querySelector('#status').textContent=JSON.stringify(response);
};
