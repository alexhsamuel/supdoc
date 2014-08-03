"use strict"

var App = angular.module('App', ['ui.router', 'ObjectModule'])

App.config(
  function ($locationProvider, $stateProvider, $urlRouterProvider) {
    $locationProvider.html5Mode(true)

    $stateProvider
      .state('index', {
        url: '/supdoc',
        templateUrl: "/title.html",
      })
      .state('module', {
        url: '/supdoc/:modname',
        templateUrl: "/module.html",
      })
      .state('object', {
        url: '/supdoc/:modname/:objname',
        templateUrl: "/object.html",
      })

  })

App.controller(
  'ApiController',
  function ($scope, $http, $q) {
    $scope.id = 'ApiController'

    var modules = {}

    /**
     * Returns a promise for the doc for a module.
     */
    function getModule(name) {
      var doc = modules[name]
      if (! defined(name)) 
        // No doc; return it.
        return promiseOf($q, undefined)
      else if (! defined(name) || doc)
        // Return the cached value.
        // FIXME: Update?
        return promiseOf($q, doc)
      else {
        var url = '/doc/' + name
        console.log('GET ' + url)

        return $http.get(url).then(
          function (response) {
            console.log('GET ' + url + ' OK')
            modules[name] = response.data
            return response.data
          },
          function (reason) {
            console.log('ERROR: GET: ' + reason)
            return undefined
          })
      }
    }
    
    $scope.moduleNames = null
    $http.get('/doc/module-list').then(function (response) {
      // FIXME: Check success.
      $scope.moduleNames = response.data
    })

    /**
     * Returns names of all modules.
     */
    $scope.getAllModnames = function () {
      return $scope.moduleNames
    }

    /**
     * Returns a promise of docs for an object, or a module if 'objname' is
     * undefined.
     */
    $scope.getObj = function (modname, objname) {
      return getModule(modname).then(
        function (mod) {
          if (! mod || ! objname)
            return mod

          var parts = objname.split('.')
          var obj = mod
          for (var i = 0; i < parts.length; ++i) {
            obj = obj.dict[parts[i]]
            if (! obj)
              return obj
          }
          return obj
        })
    }

    /**
     * Returns a promise of source lines for a module.
     */
    $scope.getSource = function (modname) {
      var url = '/src/' + modname
      console.log('GET ' + url)
      return $http.get(url).then(
        function (response) {
          console.log('GET ' + url + ' OK')
          return response.data
        },
        function (reason) {
          console.log('ERROR: GET: ' + reason)
          return undefined
        })
    }

    /**
     * Returns the last part of a dotted name.
     */
    $scope.getLastPart = function (name) {
      var parts = name.split('.')
      return parts[parts.length - 1]
    }

    /**
     * Returns the parent part of a dotted name, or null if it has non.
     */
    $scope.getParent = function (name) {
      if (name) {
        var parts = name.split('.')
        return parts.slice(0, parts.length - 1).join('.')
      }
      else
        return null
    }

  })

App.controller(
  'NavigationController', 
  function ($scope, $location, $rootScope, $state) {
    $scope.id = 'NavigationController'
    
    // On angular-ui-route state changes, set up for the new object shown.
    $rootScope.$on('$stateChangeSuccess', function (event, state, params) { 
      var modname = params.modname
      var objname = params.objname

      // Show what we're doing on the console.
      if (modname) {
        if (objname) 
          console.log('=> ' + modname + ', ' + objname)
        else
          console.log('=> ' + modname)
      }
      else
        console.log('=> module index')

      // Construct parents.
      var parents = []
      if (modname)
        modname.split('.').reduce(
          function (p, n) {
            p.push(p.length > 0 ? p[p.length - 1] + '.' + n : n)
            return p
          },
          parents)

      $scope.modname = modname
      $scope.objname = objname
      $scope.getObj(modname).then(
        function (module) { 
          $scope.module = module 
        },
        function () {
          console.log('ERROR: => ' + modname + ' failed')
          $scope.module = undefined
        }).then(
        function () { 
          $scope.getObj(modname, objname).then(function (obj) { $scope.obj = obj })
        })
      $scope.parents = parents

      // Don't load source initially.  Do this with 'loadSource'.
      $scope.source = undefined
    })

    /**
     * Joines lines of text into a string.
     */
    $scope.joinLines = function joinLines(lines) {
      if (! defined(lines))
        return undefined

      var text = ''
      for (var i = 0; i < lines.length; ++i)
        text = text + lines[i]
      return text
    }

    /**
     * Requests module source and sets $scope.source on load.
     */
    $scope.loadSource = function () {
      if (! defined($scope.source)) 
        $scope.getSource($scope.modname).then(
          function (source) {
            $scope.source = source
          },
          function () {
            console.log('ERROR: get source for ' + $scope.modname)
            $scope.source = undefined
          })
    }

    // High-level navigation methods.

    $scope.navigateToTop = function () {
      $state.go('index')
    }

    // FIXME: Merge navigateTo{Obj,Module} into this one function.
    $scope.navigateTo = function (obj) {
      if (obj.type == 'module') 
        $state.go('module', { modname: obj.name })
      else if (obj.type == 'class') 
        $state.go('object', { modname: obj.module, objname: obj.name })
      else
        console.log('ERROR: => ' + modname + ', ' + obj.name + ' (' + obj.type + ')')
    }

    $scope.navigateToObj = function (modname, objname) {
      // FIXME: if (defined(modname) && defined(objname))
      $state.go('object', { modname: modname, objname: objname })
    }

    $scope.navigateToModule = function (fullname) {
      // FIXME: if (defined(fullname))
      $state.go('module', { modname: fullname })
    }

  })

//-----------------------------------------------------------------------------
// Directives

App.directive(
  'bsPanel',
  function () {
    return {
      restrict: 'E',
      transclude: true,
      replace: true,
      scope: {
        title: '@title',
        collapsed: '=collapsed'
      },
      link: function ($scope) {
        $scope.collapseId = ('collapse' + $scope.title).replace(/[^\w]/g, '')
      },
      template: 
       '<div class="panel panel-default">\
          <div class="panel-heading">\
            <h3 class="panel-title">\
              <a class="accordion-toggle" ng-class="{collapsed: collapsed}" data-toggle="collapse" href="#{{collapseId}}">\
                {{title}}\
              </a>\
            </h3>\
          </div>\
          <div id="{{collapseId}}" class="panel-collapse collapse" ng-class="{in: ! collapsed}">\
            <div class="panel-body" ng-transclude></div>\
          </div>\
        </div>'
    }
  })

App.directive(
  'doctest', 
  ['$compile', function($compile) {
    return {
      restrict: 'E',
      transclude: true,
      replace: true,
      scope: {},
      template: '<pre ng-transclude></pre>'
    }
  }])
      
App.directive(
  'identifier',
  function () {
    return {
      restrict: 'E',
      transclude: true,
      replace: true,
      scope: {},
      template: '<span class="identifier" ng-transclude></span>'
    }
  })

App.directive(
  'module',
  function () {
    return {
      restrict: 'E',
      transclude: true,
      replace: true,
      link: function (scope, element, attrs) {
        // On click, navigate to the module.
        element.on('click', function () {
          var fullname = attrs.fullname || element.text()
          scope.navigateToModule(fullname)
        })
      },
      template: '<a class="identifier module" ng-transclude></span>'
    }
  })

function navigateOnClick(scope, element, attrs) {
  element.on('click', function () {
    // Use the 'module' attribute if present, otherwise this module.
    var modname = attrs.module || scope.modname
    // Use the 'fullname' attribute if present, otherwise the element text.
    var fullname = attrs.fullname || element.text()
    scope.navigateToObj(modname, fullname)
  })
}

App.directive(
  'class',
  function () {
    return {
      restrict: 'E',
      transclude: true,
      replace: true,
      link: navigateOnClick,
      template: '<a class="identifier class" ng-transclude></span>'
    }
  })

App.directive(
  'function',
  function () {
    return {
      restrict: 'E',
      transclude: true,
      replace: true,
      link: navigateOnClick,
      template: '<a class="identifier function" ng-transclude></span>'
    }
  })

// Includes HTML + dynamic (live) AngularJS markup into the DOM.
//
// Usage:
//
//   <ANY compile="EXPRESSION">
//
// where EXPRESSION returns HTML + AngularJS source.
App.directive(
  'compile',
  ['$compile', function ($compile) {
    return function(scope, element, attrs) {
      scope.$watch(
        function (scope) {
          return scope.$eval(attrs.compile)
        },
        function (value) {
          element.html(value)
          $compile(element.contents())(scope)
        }
      )
    }
  }])


//-----------------------------------------------------------------------------

function defined(obj) {
  return typeof obj !== 'undefined'
}

function mapObjToArr(obj, fn) {
  return Object.keys(obj).map(function (k) { return fn(k, obj[k]) })
}

//-----------------------------------------------------------------------------

// FIXME: Remove.
function lookUp(api, modname) {
  if (api == null)
    return null
  if (! defined(modname) || modname == '')
    return api
  var names = modname.split('.')
  for (var i = 0; i < names.length; ++i) {
    var name = names[i]
    if (api.modules && name in api.modules) 
      api = api.modules[name]
    else if (api.dict && name in api.dict) 
      // FIXME: Should we do this only for the last name part?
      api = api.dict[name]
    else
      return null
  }
  return api
}


function promiseOf($q, value) {
  var deferred = $q.defer()
  deferred.resolve(value)
  return deferred.promise
}


