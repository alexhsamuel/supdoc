"use strict"

var moduleListApp = angular.module('moduleListApp', [])

function ApiDocController($scope, $http) {
    $scope.modules = {}
    $http.get('apidoc.json').success(function (result) {
        $scope.modules = result
        $scope.moduleNames = Object.keys($scope.modules)
        $scope.moduleName = $scope.moduleNames[0]
    })

    $scope.module = function () { 
        return $scope.modules[$scope.moduleName] 
    }

    $scope.getByType = function (type) {
        var module = $scope.module()
        if (typeof module === 'undefined')
            return {}

        var result = {}
        for (var name in module.dict) {
            var obj = module.dict[name]
            if (obj.type == type)
                result[name] = obj
        }
        return result
    }

    $scope.getSource = function () {
        var module = $scope.module()
        if (typeof module === 'undefined')
            return ''
        var sourceLines = module.source
        var source = ""
        for (var i = 0; i < sourceLines.length; ++i) 
            source = source + sourceLines[i]
        return source
    }

    $scope.formatParameters = formatParameters
}


function formatParameters(parameters) {
    var result = "("
    var first = true
    for (var i = 0; i < parameters.length; ++i) {
        var param = parameters[i]
        if (first) 
            first = false
        else
            result += ", "
        result += param.name
    }
    result += ")"
    console.log("formatParameters")
    return result
}

