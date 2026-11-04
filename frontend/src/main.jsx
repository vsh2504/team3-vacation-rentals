// Frontend — Owner: Ranadhir Reddy Rikkala (platform)
// Entry point only: mounts App inside BrowserRouter.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
createRoot(document.getElementById('root')).render(<BrowserRouter><App /></BrowserRouter>);
