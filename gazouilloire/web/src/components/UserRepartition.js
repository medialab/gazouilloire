import React from 'react';
import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import CircularProgress from '@material-ui/core/CircularProgress';
import {BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip} from 'recharts';

const styles = theme => ({
  progress: {
    margin: theme.spacing.unit * 2
  }
});

class UnstyledUserRepartition extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      data: null
    };
  }

  componentDidMount() {
    console.log('componentDidMount');
    this._getData();
  }

  _getData() {
    console.log('_getData');
    fetch('http://127.0.0.1:5000/elasticuserrepartition')
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
        this.setState({
          data: data
        });
        console.log('json', json);
      });

    console.log('Fin _getData');
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
    console.log('Return');
    const mainData = this.state.data.splice(0, 10);
    return (
      <Grid container justify="center" alignItems="center">
        <Grid item>
          <BarChart width={1000} height={500} data={mainData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="_id" interval="0" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#247ba0" />
          </BarChart>
        </Grid>
      </Grid>
    );
  }
}

UnstyledUserRepartition.propTypes = {
  classes: PropTypes.object.isRequired
};

const UserRepartition = withStyles(styles)(UnstyledUserRepartition);

export default UserRepartition;
