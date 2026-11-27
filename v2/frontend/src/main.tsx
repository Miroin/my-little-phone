import React from 'react';
import ReactDOM from 'react-dom/client';
import {App} from './App';
import './design-system.css';
import './styles.css';
import './settings.css';
import './phase3.css';
import './phase4.css';
import './phase5.css';
import './berry-theme.css';

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
const isLocalPreview=['localhost','127.0.0.1'].includes(location.hostname);
if('serviceWorker' in navigator&&isLocalPreview)navigator.serviceWorker.getRegistrations().then(registrations=>registrations.forEach(registration=>registration.unregister())).catch(()=>{});
if('serviceWorker' in navigator&&import.meta.env.PROD&&!isLocalPreview)window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));
