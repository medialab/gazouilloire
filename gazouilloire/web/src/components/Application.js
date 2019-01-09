import React from 'react';
import {BrowserRouter as Router, Route} from 'react-router-dom';

import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import Typography from '@material-ui/core/Typography';
import TextField from '@material-ui/core/TextField';

import {MuiThemeProvider, createMuiTheme} from '@material-ui/core/styles';
import MuiPickersUtilsProvider from 'material-ui-pickers/utils/MuiPickersUtilsProvider';
import DateFnsUtils from 'material-ui-pickers/utils/date-fns-utils';

import StyledParameters from './Parameters';
import AnalyzePage from './Analyze';
import ElasticAnalyze from './ElasticAnalyze';
import TimeSeries from './TimeSeries';
import AppBar from './AppBar';
import HomePage from './HomePage';
import UserRepartition from './UserRepartition';
import Monitor from './Monitor';
import TextAnalysis from './TextAnalysis';

const drawerWidth = '350px';

const indexName = 'juliacage';
const tweetIndex = indexName.concat('_tweets');

const theme = createMuiTheme({
  palette: {
    primary: {
      light: '#70c1b3',
      main: '#247ba0',
      dark: '#247ba0',
      contrastText: '#fff'
    },
    secondary: {
      main: '#ff1654',
      dark: '#d11345',
      contrastText: '#fff'
    },
    error: {
      main: '#bc4350'
    }
  },
  typography: {
    fontFamily: "'Raleway', sans-serif"
  }
});

const styles = theme => ({
  button: {
    margin: theme.spacing.unit
  },
  input: {
    display: 'none'
  },
  mainGrid: {
    height: '100%'
  },
  root: {
    flexGrow: 1,
    minHeight: '100vh',
    zIndex: 1,
    display: 'flex',
    backgroundColor: theme.palette.background.default
  },
  appBar: {
    zIndex: theme.zIndex.drawer
  },
  drawerPaper: {
    position: 'relative',
    overflow: 'auto',
    width: drawerWidth
  },
  content: {
    flexGrow: 1,
    padding: theme.spacing.unit * 3,
    minWidth: 0 // So the Typography noWrap works
  },
  toolbar: theme.mixins.toolbar,
  body: {margin: '0px'}
});

class UnstyledApplication extends React.Component {
  constructor(props) {
    super(props);
    this.state = {index: 'default'};
  }

  updateIndex = name => {
    this.setState({
      index: name
    });
  };

  render() {
    const {classes} = this.props;
    console.log(styles.toolbar);
    let body;

    if (!this.state.index) {
      body = (
        <Grid container justify="center" alignItems="center">
          <Grid item>
            <Typography>Please specify an index name just above.</Typography>
          </Grid>
        </Grid>
      );
    } else {
      body = (
        <div>
          <Route exact path="/" component={HomePage} />
          <Route
            path="/collect"
            render={() => <StyledParameters index={tweetIndex} />}
          />
          <Route
            path="/analyze"
            render={() => <AnalyzePage index={tweetIndex} />}
          />
          <Route
            path="/elasticanalyze"
            render={() => <ElasticAnalyze index={tweetIndex} />}
          />
          <Route
            path="/timeevolution"
            render={() => <TimeSeries index={tweetIndex} />}
          />
          <Route
            path="/userrepartition"
            render={() => <UserRepartition index={tweetIndex} />}
          />
          <Route
            path="/monitor"
            render={() => <Monitor index={tweetIndex} />}
          />
          <Route
            path="/textanalysis"
            render={() => <TextAnalysis index={tweetIndex} />}
          />
        </div>
      );
    }

    return (
      <MuiPickersUtilsProvider utils={DateFnsUtils}>
        <MuiThemeProvider theme={theme}>
          <Router>
            <div
              className={classes.root}
              style={{margin: 0, float: 'top'}}
              index={tweetIndex}
            >
              <AppBar index={this.state.index} updateIndex={this.updateIndex} />

              <main style={{marginTop: '65px'}} className={classes.content}>
                {body}
              </main>
            </div>
          </Router>
        </MuiThemeProvider>
      </MuiPickersUtilsProvider>
    );
  }
}

UnstyledApplication.propTypes = {
  classes: PropTypes.object.isRequired
};

const Application = withStyles(styles)(UnstyledApplication);

export default Application;
