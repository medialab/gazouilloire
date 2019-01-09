import React from 'react';
import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import CircularProgress from '@material-ui/core/CircularProgress';
import Grid from '@material-ui/core/Grid';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import Paper from '@material-ui/core/Paper';
import Avatar from '@material-ui/core/Avatar';
import classNames from 'classnames';
import {Typography} from '@material-ui/core';
import Button from '@material-ui/core/Button';
import {BrowserRouter as Router, Route, Link} from 'react-router-dom';
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
    this._getData();
  }

  _getData() {
    fetch('http://127.0.0.1:5000/elasticdata')
      .then(response => {
        if (response.ok) {
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
        this.setState({data: json['hits']['hits']});
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
    console.log(this.state.data);
    var page = this.state.page;
    var rowsPerPage = this.state.rowsPerPage;
    const {classes} = this.props;
    var data = this.state.data;

    var tweets = data.map(function(tweet) {
      return (
        <ListItem key={tweet._id}>
          <Avatar
            src={tweet._source.user_profile_image_url}
            className={classNames(classes.avatar, classes.bigAvatar)}
          />
          <ListItemText
            primary={
              tweet._source.user_name +
              ' (@' +
              tweet._source.user_screen_name +
              ')'
            }
            secondary={tweet._source.text}
          />
        </ListItem>
      );
    });

    return (
      <Grid
        container
        direction="column"
        justify="flex-start"
        alignItems="center"
        style={{marginTop: '-15px'}}
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
        <TweetList data={this.state.data} />
      </Grid>
    );
  }
}

UnstyledAnalyzePage.propTypes = {
  classes: PropTypes.object.isRequired
};

const AnalyzePage = withStyles(styles)(UnstyledAnalyzePage);

export default AnalyzePage;
