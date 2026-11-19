import { item } from './module.js';

const bridge = window.aresosHome;
const events = [];
window.probe = { events, item };
for (const name of ['home', 'programs', 'running', 'status', 'helper']) {
  bridge.addEventListener(name, ({detail}) => events.push({name, detail}));
}
window.probe.load = async () => {
  const image = new Image();
  image.src = 'aresos-home://icon/test-web-1';
  await image.decode();
  const response = await fetch('./probe.json');
  return {
    item, data: await response.json(), type: response.headers.get('content-type'),
    image: [image.naturalWidth, image.naturalHeight], style: getComputedStyle(document.querySelector('main')).color
  };
};
