import React from 'react';
import Particles from 'react-particles-js';
import {Typography} from '@material-ui/core';

class HomePage extends React.Component {
  render() {
    return (
      <div>
        <Particles
          height="200vh"
          width="200vw"
          params={{
            particles: {
              color: {
                value: '#247ba0'
              },
              line_linked: {
                color: '#247ba0'
              },
              move: {
                direction: 'top-right',
                out_mode: 'out',
                speed: 4
              },
              number: {
                value: '300'
              },
              size: {
                value: 1
              }
            },
            interactivity: {
              events: {
                onhover: {
                  enable: false,
                  mode: 'repulse'
                }
              }
            }
          }}
          style={{
            backgroundPosition: '50% 50%',
            margin: '-50vh'
          }}
        />
        <Typography
          style={{marginLeft: 'auto', marginRight: 'auto', width: '150px'}}
        >
          Gazouilloire
        </Typography>
      </div>
    );
  }
}

export default HomePage;
