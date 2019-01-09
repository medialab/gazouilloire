import {
  LineChart,
  Line,
  Label,
  Legend,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
  ResponsiveContainer
} from 'recharts';
import React from 'react';
import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import {Typography} from '@material-ui/core';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';

const styles = theme => ({
  progress: {
    margin: theme.spacing.unit * 2
  }
});

const refreshInterval = 4;

class UnstyledIndexingRate extends React.Component {
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
    fetch('http://127.0.0.1:5000/indexstats')
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
    if (!this.state.data) {
      return (
        <Grid container justify="center" alignItems="center">
          <Grid item>
            <CircularProgress className={this.props.classes.progress} />
          </Grid>
        </Grid>
      );
    }

    var indexingRate =
      (
        (this.props.lastcount - this.props.penultimatecount) /
        refreshInterval
      ).toFixed(0) + ' tweets/s';

    return (
      <Grid container spacing={16} direction="row">
        <Grid item>
          <Typography variant="display1">
            <Icon
              color="inherit"
              style={{
                marginRight: '10px',
                marginBottom: '-4px',
                marginLeft: '-20px',
                fontSize: '32px'
              }}
            >
              av_timer
            </Icon>
            Indexing rate
          </Typography>
        </Grid>
        <Grid item>
          <Typography variant="display1" color="primary">
            {indexingRate}
          </Typography>
        </Grid>
      </Grid>
    );
  }
}

UnstyledIndexingRate.propTypes = {
  classes: PropTypes.object.isRequired
};

const IndexingRate = withStyles(styles)(UnstyledIndexingRate);

export default IndexingRate;
