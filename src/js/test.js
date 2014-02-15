"use strict"

var testApp = angular
.module('testApp', [])

.config(function ($locationProvider) {
    $locationProvider.html5Mode(true)
})

testApp.controller(
    'NavigationCtrl', 
    function ($scope, $location) {
        var routes = {
            '/test.html' : {templateUrl: 'list.html'}, 
            '/new.html'  : {templateUrl: 'new.html'}, 
            '/edit.html' : {templateUrl: 'edit.html'}
        }

        var defaultRoute = routes['/test.html']

        $scope.$watch(
            function () { 
                return $location.path()
            }, function (newPath) {
                $scope.selectedRoute = routes[newPath] || defaultRoute
            })
    })


