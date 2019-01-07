import React from 'react';
import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import CircularProgress from '@material-ui/core/CircularProgress';
import Grid from '@material-ui/core/Grid';
import classNames from 'classnames';
import Button from '@material-ui/core/Button';
import {Link} from 'react-router-dom';
import Icon from '@material-ui/core/Icon';

import TweetList from './TweetList';

const styles = theme => ({
  root: {
    width: '100%',
    marginTop: theme.spacing.unit * 3,
    overflowX: 'auto',
    flexGrow: 1
  },
  table: {
    minWidth: 700
  },
  row: {
    '&:nth-of-type(odd)': {
      backgroundColor: theme.palette.background.default
    }
  },
  card: {
    minWidth: 275
  },
  bullet: {
    display: 'inline-block',
    margin: '0 2px',
    transform: 'scale(0.8)'
  },
  title: {
    marginBottom: 16,
    fontSize: 14
  },
  pos: {
    marginBottom: 12
  },
  typo: {
    margin: '15px'
  },
  flexSection: {
    flexGrow: 1,
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
    overflow: 'auto'
  },
  paper: {
    padding: theme.spacing.unit * 2,
    textAlign: 'center',
    color: theme.palette.text.secondary
  }
});

function createTweet(id, userName, userScreenName, text) {
  return {id, userName, userScreenName, text};
}

class UnstyledAnalyzePage extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      data: null,
      rowsPerPage: 10,
      page: 0
    };
  }

  componentDidMount() {
    console.log('componentDidMount');
    this._getData();
  }

  _getData() {
    console.log('_getData');
    fetch('http://127.0.0.1:5000/elasticdata')
      .then(response => {
        if (response.ok) {
          console.log('Response ok', response);
          return response;
        } else {
          console.log('Response pas ok', response);
          let errorMessage = '${response.status(${response.statusText})',
            error = new Error(errorMessage);
          throw error;
        }
      })
      .then(response => response.json())
      .then(json => {
        this.setState({data: json});
      });
    console.log('data : ', this.state.data);
  }

  render() {
    console.log('data : ', this.state.data);
    if (!this.state.data) {
      return (
        <Grid container justify="center" alignItems="center">
          <Grid item>
            <CircularProgress className={this.props.classes.progress} />
          </Grid>
        </Grid>
      );
    }
    console.log(this.state.data);
    const {classes} = this.props;

    return (
      <Grid
        container
        direction="column"
        justify="space-between"
        alignItems="center"
        style={{marginTop: '5px', marginBottom: '20px'}}
        spacing={24}
      >
        <Grid item xs={12}>
          <Grid container justify="center" spacing={24}>
            <Grid item>
              <Button
                style={{
                  margin: '0px',
                  background:
                    'linear-gradient(45deg, #247ba0, #4278ac, #6473b0, #876bac,#bb5b89 )',
                  color: 'white'
                }}
                component={Link}
                to="/timeevolution"
                variant="extendedFab"
                className={classes.button}
              >
                <Icon
                  style={{marginRight: '8px', fontSize: 18}}
                  className={classNames(classes.icon, 'fas fa-clock')}
                />
                Time evolution
              </Button>
            </Grid>
            <Grid item>
              <Button
                style={{
                  margin: '0px',
                  background:
                    'linear-gradient(45deg, #247ba0, #4278ac, #6473b0, #876bac,#bb5b89 )',
                  color: 'white'
                }}
                component={Link}
                to="/textanalysis"
                variant="extendedFab"
                className={classes.button}
              >
                <Icon
                  style={{marginRight: '8px', fontSize: 18}}
                  className={classNames(classes.icon, 'fas fa-align-left')}
                />
                Text analysis
              </Button>
            </Grid>
            <Grid item>
              <Button
                style={{
                  margin: '0px',
                  background:
                    'linear-gradient(45deg, #247ba0, #4278ac, #6473b0, #876bac,#bb5b89 )',
                  color: 'white'
                }}
                component={Link}
                to="/userrepartition"
                variant="extendedFab"
                className={classes.button}
              >
                <Icon
                  style={{marginRight: '8px', fontSize: 18}}
                  className={classNames(classes.icon, 'fas fa-user')}
                />
                Repartition by User
              </Button>
            </Grid>
            <Grid item>
              <Button
                style={{
                  margin: '0px',
                  background:
                    'linear-gradient(45deg, #247ba0, #4278ac, #6473b0, #876bac,#bb5b89 )',
                  color: 'white'
                }}
                variant="extendedFab"
                className={classes.button}
              >
                <Icon
                  style={{marginRight: '8px', fontSize: 18}}
                  className={classNames(classes.icon, 'fas fa-mobile-alt')}
                />
                Repartition by Client
              </Button>
            </Grid>
            <Grid item>
              <Button
                style={{
                  margin: '0px',
                  background:
                    'linear-gradient(45deg, #247ba0, #4278ac, #6473b0, #876bac,#bb5b89 )',
                  color: 'white'
                }}
                variant="extendedFab"
                className={classes.button}
              >
                <Icon
                  style={{marginRight: '8px', fontSize: 18}}
                  className={classNames(classes.icon, 'fas fa-map-marker-alt')}
                />
                Repartition by location
              </Button>
            </Grid>
          </Grid>
        </Grid>
        <Grid item xs={12}>
          <TweetList data={this.state.data} />
        </Grid>
      </Grid>
    );
  }
}

UnstyledAnalyzePage.propTypes = {
  classes: PropTypes.object.isRequired
};

const AnalyzePage = withStyles(styles)(UnstyledAnalyzePage);

export default AnalyzePage;
