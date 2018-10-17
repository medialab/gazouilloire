import React from 'react';
import {render} from 'react-dom';

import Application from './components/Application';

const MOUNT_NODE = document.getElementById('app');

function renderApplication(Component) {
  const block = <Component />;
  render(block, MOUNT_NODE);
}

renderApplication(Application);

// Handling HMR
if (module.hot) {
  console.log('hot reload');
  // Reloading components
  module.hot.accept('./components/Application', () => {
    const NextApplication = require('./components/Application').default;
    renderApplication(NextApplication);
  });
}
