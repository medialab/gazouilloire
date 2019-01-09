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

const styles = theme => ({
  root: {
    width: '100%',
    marginTop: theme.spacing.unit * 3,
    overflowX: 'auto'
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
  }
});

function createTweet(id, userName, userScreenName, text) {
  return {id, userName, userScreenName, text};
}

class UnstyledTweetList extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      data: this.props.data,
      rowsPerPage: 40,
      page: 0
    };
  }

  componentDidMount() {
    if (!this.props.data) this._getData();
  }

  _getData() {
    fetch('http://127.0.0.1:5000/data')
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
        this.setState({data: json});
      });
  }

  render() {
    var page = this.state.page;
    var rowsPerPage = this.state.rowsPerPage;
    const {classes} = this.props;
    var data = this.state.data;

    if (!this.state.data) {
      return <CircularProgress className={this.props.classes.progress} />;
    }
    console.log(this.state.data);

    var tweets = data.map(function(tweet) {
      return (
        <ListItem key={tweet.tweet_id}>
          <Avatar
            src={tweet.user_profile_image_url}
            className={classNames(classes.avatar, classes.bigAvatar)}
          />
          <ListItemText
            primary={tweet.user_name + ' (@' + tweet.user_screen_name + ')'}
            secondary={tweet.text}
          />
        </ListItem>
      );
    });

    return (
      <Grid style={{marginTop: '0px'}} item xs={12}>
        <Typography style={{marginLeft: '5px'}} variant="button" gutterBottom>
          Tweets
        </Typography>
        <Paper
          className={classes.root}
          style={{marginTop: '0px', maxHeight: '500px', overflow: 'auto'}}
        >
          <List component="nav">
            {tweets.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)}
          </List>
        </Paper>
      </Grid>
    );
  }
}

UnstyledTweetList.propTypes = {
  classes: PropTypes.object.isRequired
};

const TweetList = withStyles(styles)(UnstyledTweetList);

export default TweetList;
