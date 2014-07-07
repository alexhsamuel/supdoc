"use strict"

var App = angular.module('App', ['ngRoute', 'ObjectModule'])

App.config(
  function ($locationProvider, $routeProvider) {
    $locationProvider.html5Mode(true)
    $routeProvider
      .when('/doc', { templateUrl: '/title.html' })
      .when('/doc/:fullname', { templateUrl: '/module.html' }) 
      .when('/doc/:fullname/:name', { templateUrl: '/class.html' })
      .otherwise({ templateUrl: '/error.html' }) 
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

    $scope.getApi = function (moduleName) { 
      return lookUp($scope.top, moduleName) 
    }

  })

App.controller(
  'NavigationController', 
  function ($scope, $location, $routeParams) {
    $scope.id = 'NavigationController'
    
    function onNav() {
      var fullname = $scope.moduleName
      var name = $scope.name

      // Fish out the API for the containing module.
      $scope.module = $scope.getModule(fullname)
      $scope.obj = $scope.module && $scope.name ? $scope.module.dict[$scope.name] : null

      // Construct parents.
      $scope.parents = []
      if (fullname)
        fullname.split('.').reduce(
          function (p, n) {
            p.push(p.length > 0 ? p[p.length - 1] + '.' + n : n)
            return p
          },
          $scope.parents)

      // Update the location.
      var location = "/doc"
      if (isDefined(fullname)) {
        location += "/" + fullname
        if (name) {
          location += "/" + name
        }
      }
      console.log("location -> " + location)
      $location.path(location)
    }

    $scope.$watch('moduleName', onNav)
    $scope.$watch('name', onNav)

    $scope.navigateToTop = function () {
      $scope.moduleName = ''
    }

    $scope.navigateTo = function(obj) {
      if (obj.type == "module") 
        $scope.navigateToModule(obj.name)
      else if (obj.type == "class") {
        console.log("nav: class: " + obj.name + " in " + obj.module)
        $scope.moduleName = obj.module
        $scope.name = obj.name
      }
    }

    $scope.navigateToModule = function (fullname) {
      if ($scope.getModule(fullname)) {
        console.log("navigateToModule " + fullname)
        $scope.moduleName = fullname
        $scope.name = ""
      }
      else {
        console.log("navigateToModule: " + fullname + " not found")
      }
    }

    $scope.getLastPart = function (moduleName) {
      var parts = moduleName.split('.')
      return parts[parts.length - 1]
    }

    $scope.getParent = function (moduleName) {
      if (moduleName) {
        var parts = moduleName.split('.')
        return parts.slice(0, parts.length - 1).join('.')
      }
      else
        return null
    }

    // Watch for location changes.  This also initializes moduleName.
    $scope.$watch(
      function () { 
        console.log("route fullname: " + $routeParams.fullname)
        return $routeParams.fullname
      },
      function (fullname) { 
        console.log("nav: from URI: " + fullname)
        $scope.moduleName = fullname
      })
    $scope.$watch(
      function () {
        console.log("route name: " + $routeParams.name)
        return $routeParams.name
      },
      function (name) {
        console.log("nav: from URI: " + name + " in " + $scope.moduleName)
        $scope.name = name
      })

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
        console.log(element)
        var fullname = attrs.fullname || element.text()
        element.on('click', function () {
          // FIXME: Doesn't quite work.
          console.log('module click DOES NOT WORK')
          scope.navigateToModule(fullname)
        })
      },
      template: '<span class="module" ng-transclude></span>'
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

