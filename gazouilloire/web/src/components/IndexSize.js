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
  var data_size = tickItem / (1024 * 1024);
  var data_size_str;
  if (data_size > 1000) data_size_str = (data_size / 1000).toFixed(2) + ' GB';
  else data_size_str = data_size.toFixed(2) + ' MB';
  return data_size_str;
}

class UnstyledIndexSize extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      data: this.props.data
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

    var data = this.props.data['indices'][this.props.index + '_tweets'][
      'primaries'
    ]['store']['size_in_bytes'];

    return (
      <Grid container spacing={16}>
        <Grid
          container
          spacing={16}
          direction="row"
          style={{marginBottom: '5px'}}
        >
          <Grid item>
            <Typography variant="display1">
              <Icon
                className={classNames(classes.icon, 'fa fa-hdd')}
                style={{
                  marginRight: '15px',
                  marginBottom: '2px',
                  marginLeft: '-6px'
                }}
                color="inherit"
              />
              Disk usage
            </Typography>
          </Grid>
          <Grid item>
            <Typography variant="display1" color="primary">
              {formatYAxis(data)}
            </Typography>
          </Grid>
        </Grid>
        <Grid item>
          <LineChart
            width={500}
            height={250}
            data={this.props.sizeXAxis}
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
              domain={['auto', 'auto']}
              scale="auto"
              tickFormatter={formatYAxis}
            />
            <Tooltip
              labelFormatter={formatXAxis}
              formatter={count => formatYAxis(count)}
            />
            <Line
              type="monotone"
              dataKey="size"
              stroke="#247ba0"
              name="Storage size"
              dot={false}
            />
          </LineChart>
        </Grid>
      </Grid>
    );
  }
}

UnstyledIndexSize.propTypes = {
  classes: PropTypes.object.isRequired
};

const IndexSize = withStyles(styles)(UnstyledIndexSize);

export default IndexSize;
