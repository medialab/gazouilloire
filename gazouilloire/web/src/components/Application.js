import React from 'react';
import {BrowserRouter as Router, Route} from 'react-router-dom';

import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';

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

const drawerWidth = '350px';

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

function UnstyledApplication(props) {
  const {classes} = props;
  console.log(styles.toolbar);
  return (
    <MuiPickersUtilsProvider utils={DateFnsUtils}>
      <MuiThemeProvider theme={theme}>
        <Router>
          <div className={classes.root} style={{margin: 0, float: 'top'}}>
            <AppBar />

            <main style={{marginTop: '65px'}} className={classes.content}>
              <Route exact path="/" component={HomePage} />
              {/*<Grid
                container
                className={classes.mainGrid}
                spacing={24}
                justify="center"
                alignItems="stretch"
                style={{marginTop: '10px'}}
              >
                <Grid item>*/}
              <Route path="/collect" component={StyledParameters} />
              <Route path="/analyze" component={AnalyzePage} />
              <Route path="/elasticanalyze" component={ElasticAnalyze} />
              <Route path="/timeevolution" component={TimeSeries} />
              <Route path="/userrepartition" component={UserRepartition} />
              <Route path="/monitor" component={Monitor} />
            </main>
          </div>
        </Router>
      </MuiThemeProvider>
    </MuiPickersUtilsProvider>
  );
}

UnstyledApplication.propTypes = {
  classes: PropTypes.object.isRequired
};

const Application = withStyles(styles)(UnstyledApplication);

export default Application;
