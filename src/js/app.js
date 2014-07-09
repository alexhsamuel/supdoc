"use strict"

var App = angular.module('App', ['ui.router', 'ObjectModule'])

App.config(
  function ($locationProvider, $stateProvider, $urlRouterProvider) {
    $locationProvider.html5Mode(true)

    $stateProvider
      .state('index', {
        url: '/doc',
        templateUrl: "/title.html",
      })
      .state('module', {
        url: '/doc/:moduleName',
        templateUrl: "/module.html",
      })
      .state('object', {
        url: '/doc/:moduleName/:name',
        templateUrl: "/object.html",
      })

  })

App.controller(
  'ApiController',
  function ($scope, $http) {
    $scope.id = 'ApiController'

    // Load up all the API data.
    $scope.top = null
    $http.get('/apidoc.json').success(
      function (result) {
        $scope.top = result
      })

    $scope.getModuleFqnames = function () {
      return Object.keys($scope.top.modules)
    }

    $scope.getModule = function (fullname) {
      return $scope.top != null ? $scope.top.modules[fullname] : undefined
    }

    $scope.getObj = function (modname, objname) {
      var mod = $scope.getModule(modname)
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
    }

    $scope.getApi = function (moduleName) { 
      return lookUp($scope.top, moduleName) 
    }

    /**
     * Returns the last part of a dotted name.
     */
    $scope.getLastPart = function (name) {
      console.log("getLastPart(" + name + ")")
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
      var moduleName = params.moduleName
      var name = params.name

      // Show what we're doing on the console.
      if (moduleName) {
        if (name) 
          console.log("navigate to object " + name + " in module " + moduleName)
        else
          console.log("navigate to module " + moduleName)
      }
      else
        console.log("navigate to top")

      // Construct parents.
      var parents = []
      if (moduleName)
        moduleName.split('.').reduce(
          function (p, n) {
            p.push(p.length > 0 ? p[p.length - 1] + '.' + n : n)
            return p
          },
          parents)

      $scope.moduleName = moduleName
      $scope.name = name
      $scope.module = $scope.getModule(moduleName)
      $scope.obj = $scope.getObj(moduleName, name)
      $scope.parents = parents
    })

    // High-level navigation methods.

    $scope.navigateToTop = function () {
      $state.go('index')
    }

    // FIXME: Merge navigateTo{Obj,Module} into this one function.
    $scope.navigateTo = function (obj) {
      if (obj.type == 'module') 
        $state.go('module', { moduleName: obj.name })
      else if (obj.type == 'class') 
        $state.go('object', { moduleName: obj.module, name: obj.name })
      else
        console.log("can't navigate to " + obj.name + " of type " + obj.type)
    }

    $scope.navigateToObj = function (modname, objname) {
      if ($scope.getObj(modname, objname))
        $state.go('object', { moduleName: modname, name: objname })
      else
        console.log("navigateToObj: " + modname + "/" + objname + " not found")
    }

    $scope.navigateToModule = function (fullname) {
      if ($scope.getModule(fullname)) {
        $state.go('module', { moduleName: fullname })
      }
      else {
        console.log("navigateToModule: " + fullname + " not found")
      }
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
    var modname = attrs.module || scope.moduleName
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

function isUndefined(obj) {
  return typeof obj === 'undefined'
}

function isDefined(obj) {
  return typeof obj !== 'undefined'
}

function mapObjToArr(obj, fn) {
  return Object.keys(obj).map(function (k) { return fn(k, obj[k]) })
}

//-----------------------------------------------------------------------------

// FIXME: Remove.
function lookUp(api, moduleName) {
  if (api == null)
    return null
  if (isUndefined(moduleName) || moduleName == '')
    return api
  var names = moduleName.split('.')
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

