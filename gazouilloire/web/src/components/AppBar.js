import React from 'react';

import {Link} from 'react-router-dom';
import MaterialAppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import Icon from '@material-ui/core/Icon';
import classNames from 'classnames';
import Typography from '@material-ui/core/Typography';
import Button from '@material-ui/core/Button';
import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import TextField from '@material-ui/core/TextField';
import grey from '@material-ui/core/colors/grey';

const drawerWidth = '350px';

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
    height: 'calc(100vh - 16px)',
    zIndex: 1,
    overflow: 'hidden',
    display: 'flex'
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
    backgroundColor: theme.palette.background.default,
    padding: theme.spacing.unit * 3,
    minWidth: 0 // So the Typography noWrap works
  },
  toolbar: theme.mixins.toolbar
});

class UnstyledAppBar extends React.Component {
  handleSubmit = e => {
    e.preventDefault();
    this.props.updateIndex;
  };

  handleChange = e => {};

  render() {
    const {classes} = this.props;

    return (
      <MaterialAppBar position="absolute" className={classes.appBar}>
        <Toolbar>
          <Icon
            component={Link}
            to="/"
            style={{margin: '10px'}}
            className={classNames(classes.icon, 'fab fa-twitter')}
          />
          <Typography
            component={Link}
            to="/"
            variant="title"
            color="inherit"
            noWrap
            style={{flex: 1, textDecoration: 'none', outline: 0}}
          >
            Gazouilloire
          </Typography>
          <form
            className={classes.container}
            onSubmit={this.handleSubmit}
            noValidate
            autoComplete="off"
          >
            <TextField
              id="outlined-name"
              label="Index"
              className={classes.textField}
              onChange={this.handleChange}
              value={this.props.index}
              margin="normal"
              variant="outlined"
              style={{borderColor: grey[50], color: grey[50], margin: '10px'}}
              margin="dense"
            />
          </form>
          <Button
            component={Link}
            to="/monitor"
            variant="outlined"
            style={{
              color: 'white',
              border: 'solid 1px white'
            }}
            className={classes.button}
          >
            Monitor
          </Button>
          <Button
            component={Link}
            to="/collect"
            variant="contained"
            style={{
              background: 'white',
              fontWeight: 'bold',
              color: '#247ba0'
            }}
            className={classes.button}
          >
            Collect
          </Button>
          <Button
            component={Link}
            to="/analyze"
            variant="contained"
            color="default"
            style={{
              background: 'white',
              fontWeight: 'bold',
              color: '#247ba0'
            }}
            className={classes.button}
          >
            Analyze
          </Button>
        </Toolbar>
      </MaterialAppBar>
    );
  }
}

UnstyledAppBar.propTypes = {
  classes: PropTypes.object.isRequired
};

const AppBar = withStyles(styles)(UnstyledAppBar);

export default AppBar;
