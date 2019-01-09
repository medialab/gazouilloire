import React from 'react';
import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';
import classNames from 'classnames';
import Button from '@material-ui/core/Button';
import green from '@material-ui/core/colors/green';

import DocCount from './DocCount';
import IndexSize from './IndexSize';
import IndexingRate from './IndexingRate';
import {Typography} from '@material-ui/core';

const styles = theme => ({
  progress: {
    margin: theme.spacing.unit * 2
  },
  root: {
    ...theme.mixins.gutters(),
    paddingTop: theme.spacing.unit * 2,
    paddingBottom: theme.spacing.unit * 2
  }
});

const refreshInterval = 4;

const initialState = {
  data: null,
  lastcount: null,
  penultimatecount: null,
  countXAxis: [],
  sizeXAxis: []
};

class UnstyledMonitor extends React.Component {
  constructor(props) {
    super(props);
    this.state = initialState;
    this._getData = this._getData.bind(this);
  }

  componentDidMount() {
    this.interval = setInterval(this._getData, refreshInterval * 1000);
    this._getData();
  }

  componentWillUnmount() {
    if (typeof this.interval === 'number') clearInterval(this.interval);
  }

  _getData() {
    fetch('http://127.0.0.1:5000/indexstats')
      .then(response => {
        if (response.ok) {
          console.log('Flask server response ok', response);
          return response;
        } else {
          console.log('Flask server response not ok', response);
          let errorMessage = '${response.status(${response.statusText})',
            error = new Error(errorMessage);
          throw error;
        }
      })
      .then(response => response.json())
      .then(json => {
        const data = json;
        if (!this.state.penultimatecount)
          var penultimatecount =
            data['indices'][this.props.index]['primaries']['docs']['count'];
        else var penultimatecount = this.state.lastcount;
        var lastcount =
          data['indices'][this.props.index]['primaries']['docs']['count'];
        var now = new Date();
        var newCountXAxis = this.state.countXAxis.concat({
          time: now.getTime(),
          count: lastcount
        });
        var data_size =
          data['indices'][this.props.index]['primaries']['store'][
            'size_in_bytes'
          ];
        var newSizeXAxis = this.state.sizeXAxis.concat({
          time: now.getTime(),
          size: data_size
        });
        this.setState({
          data: data,
          lastcount: lastcount,
          penultimatecount: penultimatecount,
          countXAxis: newCountXAxis,
          sizeXAxis: newSizeXAxis
        });
      });
  }
  render() {
    var data = this.state.data;
    const {classes} = this.props;

    if (!this.state.data) {
      return (
        <Grid container justify="center" alignItems="center">
          <Grid item>
            <CircularProgress className={this.props.classes.progress} />
          </Grid>
        </Grid>
      );
    }

    var collect_state;
    var collect_state_color;
    const ok = green;
    var countXAxis = this.state.countXAxis;
    if (!countXAxis[countXAxis.length - 5]) {
      collect_state = 'OFF';
      collect_state_color = '#F44336';
    } else if (
      this.state.lastcount - this.state.penultimatecount === 0 &&
      countXAxis[countXAxis.length - 2].count -
        countXAxis[countXAxis.length - 3].count ===
        0 &&
      countXAxis[countXAxis.length - 3].count -
        countXAxis[countXAxis.length - 4].count ===
        0 &&
      countXAxis[countXAxis.length - 4].count -
        countXAxis[countXAxis.length - 5].count ===
        0
    ) {
      collect_state = 'OFF';
      collect_state_color = '#F44336';
    } else {
      collect_state = 'ON';
      collect_state_color = '#4CAF50';
    }

    return (
      <Grid container spacing={40} style={{padding: '30px'}} direction="column">
        <Grid item>
          <Button
            variant="outlined"
            disabled
            style={{
              textTransform: 'none',
              marginLeft: '-15px',
              marginBottom: '0px',
              marginTop: '-15px',
              border: '0px solid',
              background: '#D3D3D3'
            }}
          >
            <Grid container spacing={8} direction="row">
              <Grid item>
                <Typography variant="display1" style={{color: 'white'}}>
                  Index
                </Typography>
              </Grid>
              <Grid item>
                <Typography
                  variant="display1"
                  style={{fontStyle: 'italic'}}
                  color="primary"
                >
                  {this.props.index}
                </Typography>
              </Grid>
            </Grid>
          </Button>
        </Grid>
        <Grid item>
          <Grid container spacing={32} direction="column">
            <Grid container spacing={16} direction="row">
              <Grid item>
                <Typography variant="display1">
                  <Icon
                    style={{
                      marginRight: '14px',
                      marginBottom: '2px'
                    }}
                    className={classNames(classes.icon, 'fas fa-power-off')}
                    color="inherit"
                  />
                  Collect state
                </Typography>
              </Grid>
              <Grid item>
                <Typography
                  variant="display1"
                  style={{color: collect_state_color}}
                >
                  {collect_state}
                </Typography>
              </Grid>
            </Grid>
            <Grid item>
              <IndexingRate
                data={this.state.data}
                lastcount={this.state.lastcount}
                penultimatecount={this.state.penultimatecount}
                index={this.props.index}
              />
            </Grid>
            <Grid item>
              <Grid container spacing={16}>
                <Grid item xs>
                  <DocCount
                    data={this.state.data}
                    countXAxis={this.state.countXAxis}
                    index={this.props.index}
                  />
                </Grid>
                <Grid item xs>
                  <IndexSize
                    data={this.state.data}
                    sizeXAxis={this.state.sizeXAxis}
                    index={this.props.index}
                  />
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    );
  }
}

UnstyledMonitor.propTypes = {
  classes: PropTypes.object.isRequired
};

const Monitor = withStyles(styles)(UnstyledMonitor);

export default Monitor;
