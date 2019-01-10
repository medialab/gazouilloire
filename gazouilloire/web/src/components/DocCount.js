import {LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip} from 'recharts';
import React from 'react';
import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import {Typography} from '@material-ui/core';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';
import classNames from 'classnames';

const styles = theme => ({
  progress: {
    margin: theme.spacing.unit * 2
  }
});

function formatXAxis(tickItem) {
  var date = new Date(tickItem);
  var hours = date.getHours();
  hours = ('0' + hours).slice(-2);
  var minutes = date.getMinutes();
  minutes = ('0' + minutes).slice(-2);
  return hours + ':' + minutes;
}

function formatYAxis(tickItem) {
  var res;
  if (tickItem > 1000 && tickItem < 1000000) {
    if (tickItem % 1000 === 0) res = Math.floor(tickItem / 1000) + 'k';
    else res = (tickItem / 1000).toFixed(2) + 'k';
  } else if (tickItem > 1000000) {
    if (tickItem % 1000000 === 0) res = Math.floor(tickItem / 1000000) + 'm';
    else res = (tickItem / 1000000).toFixed(2) + 'm';
  } else {
    res = tickItem.toFixed(0);
  }
  return res;
}

class UnstyledDocCount extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      data: this.props.data,
      xaxis: []
    };
  }

  componentDidMount() {
    if (!this.props.data) this._getData();
  }

  _getData() {
    fetch(
      'http://127.0.0.1:5000/indexstats?index=' + this.props.index + '_tweets'
    )
      .then(response => {
        if (response.ok) {
          return response;
        } else {
          let errorMessage = '${response.status(${response.statusText})',
            error = new Error(errorMessage);
          throw error;
        }
      })
      .then(response => response.json())
      .then(json => {
        const data = json;
        this.setState({
          data: data
        });
      });
  }

  render() {
    var data = this.props.data;
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

    var docCount = this.props.data['indices'][this.props.index + '_tweets'][
      'primaries'
    ]['docs']['count'];

    return (
      <Grid container spacing={16} style={{marginTop: '-15px'}}>
        <Grid
          container
          spacing={16}
          direction="row"
          style={{marginBottom: '5px'}}
        >
          <Grid item>
            <Typography variant="display1">
              <Icon
                className={classNames(classes.icon, 'fa fa-database')}
                style={{
                  marginRight: '15px',
                  marginBottom: '2px',
                  marginLeft: '-6px'
                }}
                color="inherit"
              />
              Tweet count
            </Typography>
          </Grid>
          <Grid item>
            <Typography variant="display1" color="primary">
              {docCount.toLocaleString('fr-FR')}
            </Typography>
          </Grid>
        </Grid>
        <Grid item>
          <LineChart
            width={500}
            height={250}
            data={this.props.countXAxis}
            style={{
              fontFamily: 'Raleway'
            }}
            margin={{top: 5, right: 30, left: 20, bottom: 5}}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="time"
              tickFormatter={formatXAxis}
              interval={Math.floor(data.length / 10)}
            />
            <YAxis
              tickFormatter={formatYAxis}
              domain={['auto', 'auto']}
              scale="auto"
            />
            <Tooltip
              labelFormatter={formatXAxis}
              formatter={count => count.toLocaleString('fr-FR')}
            />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#247ba0"
              name="Tweet count"
              dot={false}
            />
          </LineChart>
        </Grid>
      </Grid>
    );
  }
}

UnstyledDocCount.propTypes = {
  classes: PropTypes.object.isRequired
};

const DocCount = withStyles(styles)(UnstyledDocCount);

export default DocCount;
